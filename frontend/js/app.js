let buildStartTime;

function switchTab(index) {
    if (index === 1) {
        alert("📁 File upload is coming soon in v1.1!\nFor now, please use the GitHub Repository tab.");
        return;
    }
    
    document.querySelectorAll('.tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === index);
    });
    document.querySelectorAll('.tab-content').forEach((content, i) => {
        content.classList.toggle('active', i === index);
    });
}

// OS selection is locked to Windows
function selectOS(element) {
    const osValue = element.querySelector('input').value;
    if (osValue !== 'windows') {
        alert("🖥️ Only Windows builds are supported in this version.\nmacOS and Linux support coming soon!");
        return;
    }
    
    document.querySelectorAll('.os-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
    element.querySelector('input').checked = true;
}

function updateProgress(percent, message) {
    document.getElementById('progressBar').style.width = percent + '%';
    document.getElementById('statusText').textContent = message;
}

function showStatus(show = true) {
    document.getElementById('statusSection').classList.toggle('active', show);
}

function showDownload(show = true, downloadUrl = '', buildTime = 0, fileSize = 0) {
    const downloadSection = document.getElementById('downloadSection');
    downloadSection.classList.toggle('active', show);
    if (show) {
        document.getElementById('downloadLink').href = downloadUrl;
        document.getElementById('buildTime').textContent = buildTime;
        document.getElementById('fileSize').textContent = fileSize;
    }
}

async function startBuild() {
    const buildBtn = document.getElementById('buildBtn');
    let repoUrl = document.getElementById('repoUrl').value.trim();
    
    // ✅ CLEAN URL: Remove query parameters and fragments
    if (repoUrl.includes('?')) {
        repoUrl = repoUrl.split('?')[0];
    }
    if (repoUrl.includes('#')) {
        repoUrl = repoUrl.split('#')[0];
    }
    repoUrl = repoUrl.replace(/\/+$/, ''); // Remove trailing slashes
    
    if (!repoUrl) {
        alert('Please enter a GitHub repository URL');
        return;
    }

    // ✅ FIXED VALIDATION: No trailing spaces!
    if (!repoUrl.startsWith('https://github.com/')) {
        alert('Please enter a valid GitHub URL (must start with https://github.com/)');
        return;
    }

    buildBtn.disabled = true;
    buildBtn.textContent = '🔄 Building...';
    showStatus(true);
    showDownload(false);
    buildStartTime = Date.now();

    try {
        // Step 1: Analyze repo
        updateProgress(10, '🔍 Analyzing repository...');
        const analyzeRes = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: repoUrl })
        });

        // ✅ Handle non-JSON responses (like HTML error pages)
        if (!analyzeRes.ok) {
            throw new Error('Repository analysis failed');
        }
        
        const contentType = analyzeRes.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Invalid response from server (not JSON)');
        }

        const analysis = await analyzeRes.json();
        if (!analysis.can_build) {
            const errorMsg = analysis.error || 
                (analysis.issues && analysis.issues.length > 0 
                    ? 'Security issues: ' + analysis.issues.join('; ')
                    : 'Cannot build this repository');
            updateProgress(0, `❌ ${errorMsg}`);
            setTimeout(() => showStatus(false), 4000);
            return;
        }

        // Step 2: Build
        updateProgress(30, '📥 Cloning repository...');
        const buildRes = await fetch('/api/build', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: repoUrl })
        });

        if (!buildRes.ok) {
            throw new Error('Build request failed');
        }
        
        const buildContentType = buildRes.headers.get('content-type');
        if (!buildContentType || !buildContentType.includes('application/json')) {
            throw new Error('Invalid build response (not JSON)');
        }

        const result = await buildRes.json();
        if (!result.build_id) {
            throw new Error(result.error || 'Build failed');
        }

        // Simulate remaining progress
        updateProgress(60, '⚙️ Compiling executable...');
        await new Promise(r => setTimeout(r, 2000));
        updateProgress(90, '📋 Packaging...');
        await new Promise(r => setTimeout(r, 1000));

        updateProgress(100, '✅ Build complete!');
        const buildTime = Math.round((Date.now() - buildStartTime) / 1000);
        showDownload(true, `/api/download/${result.build_id}`, buildTime, '2.3');

    } catch (error) {
        console.error('Build error:', error);
        updateProgress(0, `❌ ${error.message}`);
        setTimeout(() => showStatus(false), 4000);
    }

    buildBtn.disabled = false;
    buildBtn.textContent = '🔨 Build Executable';
}

// Enter key support
document.getElementById('repoUrl').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        startBuild();
    }
});

// Initialize: ensure Windows is selected
document.addEventListener('DOMContentLoaded', function() {
    const windowsOption = document.querySelector('input[value="windows"]').closest('.os-option');
    windowsOption.classList.add('selected');
});