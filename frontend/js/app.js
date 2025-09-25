let buildStartTime;

function switchTab(index) {
    if (index === 1) {
        alert("File upload functionality is planned for a future release.\nPlease use the GitHub Repository option for now.");
        return;
    }

    document.querySelectorAll('.tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === index);
    });
    document.querySelectorAll('.tab-content').forEach((content, i) => {
        content.classList.toggle('active', i === index);
    });
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
        // fileSize element was removed from HTML - skip it
    }
}

async function pollBuildStatus(buildId) {
    /**
     * Poll the build status endpoint until build completes
     */
    const maxAttempts = 60; // 5 minutes max (5s intervals)
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const statusRes = await fetch(`/api/status/${buildId}`);
            if (!statusRes.ok) {
                throw new Error('Failed to get build status');
            }

            const status = await statusRes.json();
            console.log('Build status:', status);

            if (status.status === 'completed') {
                updateProgress(100, 'Build complete');
                const buildTime = Math.round((Date.now() - buildStartTime) / 1000);
                showDownload(true, `/api/download/${buildId}`, buildTime);
                return true;
            } else if (status.status === 'failed') {
                const errorMsg = status.error || status.result?.error || 'Build failed';
                updateProgress(0, `❌ ${errorMsg}`);
                setTimeout(() => showStatus(false), 8000);
                return false;
            } else if (status.status === 'not_found') {
                updateProgress(0, '❌ Build not found');
                setTimeout(() => showStatus(false), 8000);
                return false;
            }

            // Still building - update progress
            const elapsed = (Date.now() - buildStartTime) / 1000;
            if (elapsed < 30) {
                updateProgress(20, 'Cloning repository...');
            } else if (elapsed < 120) {
                updateProgress(50, 'Building executable...');
            } else {
                updateProgress(80, 'Packaging application...');
            }

            attempts++;
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds

        } catch (error) {
            console.error('Status polling error:', error);
            updateProgress(0, `❌ Status check failed: ${error.message}`);
            setTimeout(() => showStatus(false), 8000);
            return false;
        }
    }

    // Timeout
    updateProgress(0, '❌ Build timed out (5 minutes)');
    setTimeout(() => showStatus(false), 4000);
    return false;
}

async function startBuild() {
    const buildBtn = document.getElementById('buildBtn');
    let repoUrl = document.getElementById('repoUrl').value.trim();

    // Clean URL: Remove query parameters and fragments
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
        // Step 1: Analyze repository
        updateProgress(10, 'Analyzing repository...');
        const analyzeRes = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: repoUrl })
        });

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
            setTimeout(() => showStatus(false), 8000);
            return;
        }

        // Step 2: Start build
        updateProgress(15, 'Starting build process...');
        const buildRes = await fetch('/api/build', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: repoUrl })
        });

        if (!buildRes.ok) {
            const errorText = await buildRes.text();
            throw new Error(`Build request failed: ${buildRes.status} ${errorText}`);
        }

        const buildContentType = buildRes.headers.get('content-type');
        if (!buildContentType || !buildContentType.includes('application/json')) {
            const responseText = await buildRes.text();
            throw new Error(`Invalid build response: ${responseText}`);
        }

        const result = await buildRes.json();

        // Handle security warning with user choice
        if (!result.build_id && result.security_warning) {
            const userChoice = confirm(
                `⚠️ SECURITY WARNING\n\n${result.error}\n\n` +
                `Do you trust this repository and want to build it anyway?\n\n` +
                `Click OK to continue at your own risk, or Cancel to stop.`
            );

            if (userChoice) {
                // Retry with force_build=true
                updateProgress(15, 'Building with security override...');
                const forceRes = await fetch('/api/build', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: repoUrl, force_build: true })
                });

                if (!forceRes.ok) {
                    throw new Error('Forced build failed');
                }

                const forceResult = await forceRes.json();
                if (!forceResult.build_id) {
                    throw new Error(forceResult.error || 'Forced build failed to start');
                }

                console.log('Forced build started with ID:', forceResult.build_id);
                updateProgress(20, 'Build in progress...');
                await pollBuildStatus(forceResult.build_id);
                return;
            } else {
                updateProgress(0, '❌ Build cancelled by user');
                setTimeout(() => showStatus(false), 6000);
                return;
            }
        }

        if (!result.build_id) {
            throw new Error(result.error || 'Build failed to start');
        }

        console.log('Build started with ID:', result.build_id);

        // Step 3: Poll for completion
        updateProgress(20, 'Build in progress...');
        await pollBuildStatus(result.build_id);

    } catch (error) {
        console.error('Build error:', error);

        // Check if this is a paid tier limitation
        if (error.message.includes('PyInstaller requires paid hosting')) {
            updateProgress(0, '❌ Free tier limitation - Repository analysis passed!');
            showDetailedError('✅ Good news! Your repository passed all security checks and is ready to build.\n\n❌ However, PyInstaller requires paid hosting tier.\n\n💡 Help us upgrade to paid hosting ($7/month) by using the Support button above.');
        } else {
            updateProgress(0, `❌ ${error.message}`);
            setTimeout(() => showStatus(false), 8000); // Extended to 8 seconds
        }
    } finally {
        buildBtn.disabled = false;
        buildBtn.textContent = 'Build Executable';
    }
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

// Donation modal function
function showDonationInfo() {
    const donationHTML = `
        <div class="donation-modal" id="donationModal">
            <div class="donation-content">
                <h3>Support This Project</h3>
                <p>Help keep this free tool running and improve build capabilities.</p>

                <div class="donation-options">
                    <div class="donation-method">
                        <strong>Send Bitcoin Tip:</strong>
                        <p>Visit <a href="https://x.com/iamGudfred" target="_blank">x.com/iamGudfred</a> and use the tip icon</p>
                        <p class="btc-address">1H1KFHWxAkySDyuSR9hTaVymnzgE5G9yDc</p>
                    </div>
                    <div class="donation-method">
                        <strong>Goal:</strong>
                        <p>Upgrade to paid hosting ($7/month) for faster, more reliable builds</p>
                    </div>
                    <div class="donation-method">
                        <strong>Free Support:</strong>
                        <p>Star the repository and share with others who need this tool</p>
                    </div>
                </div>

                <div class="donation-actions">
                    <a href="https://x.com/iamGudfred" target="_blank" class="donation-btn primary">
                        Visit X Profile
                    </a>
                    <button class="donation-btn secondary" onclick="closeDonationModal()">
                        Close
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', donationHTML);
}

function closeDonationModal() {
    const modal = document.getElementById('donationModal');
    if (modal) {
        modal.remove();
    }
}

function showDetailedError(message) {
    const errorHTML = `
        <div class="donation-modal" id="errorModal">
            <div class="donation-content">
                <h3>Build Status</h3>
                <div style="white-space: pre-line; text-align: left; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 8px; margin: 15px 0;">
                    ${message}
                </div>
                <div class="donation-actions">
                    <button class="donation-btn secondary" onclick="closeErrorModal()">
                        Got it
                    </button>
                    <button class="donation-btn primary" onclick="closeErrorModal(); showDonationInfo()">
                        Support Us
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', errorHTML);
}

function closeErrorModal() {
    const modal = document.getElementById('errorModal');
    if (modal) {
        modal.remove();
    }
}

// About/Story modal function
function showAboutStory() {
    const aboutHTML = `
        <div class="donation-modal" id="aboutModal">
            <div class="donation-content" style="max-width: 650px; max-height: 90vh; overflow-y: auto;">
                <h3>Why We Built This Tool</h3>

                <div class="story-section">
                    <h4>The Problem</h4>
                    <p>Millions of non-technical users find amazing Python projects on GitHub but feel frustrated. They see useful calculators, games, and tools but can't run them without installing Python, managing dependencies, or using command lines.</p>
                    <p>A viral tweet captured this perfectly: "Why can't I just download and run this? I don't want to become a developer just to use a calculator!"</p>
                </div>

                <div class="story-section">
                    <h4>Our Mission</h4>
                    <p>Bridge the gap between developers and everyday users. We believe useful software should be accessible to everyone, regardless of technical knowledge.</p>
                    <p>This tool converts Python repositories into ready-to-run Windows executables with just a URL paste and click.</p>
                </div>

                <div class="story-section">
                    <h4>Open Source Vision</h4>
                    <p><strong>Current:</strong> Python to Windows .exe files</p>
                    <p><strong>Roadmap:</strong> We're making this open source so global developers can expand it to support:</p>
                    <ul style="text-align: left; margin: 10px 0;">
                        <li>macOS applications (.app files)</li>
                        <li>Linux executables</li>
                        <li>JavaScript/Node.js projects</li>
                        <li>Go, Rust, and other languages</li>
                        <li>Mobile app generation</li>
                    </ul>
                </div>

                <div class="story-section">
                    <h4>Built by Frustrated Users, For Frustrated Users</h4>
                    <p>Created by <strong>Godfred Prebbie Mensah</strong>, a lifelong learner who experienced the same frustration. This is our contribution to making software more accessible.</p>
                    <p>Every star, share, and donation helps us grow this into a global solution.</p>
                </div>

                <div class="donation-actions">
                    <button class="donation-btn secondary" onclick="closeAboutModal()">
                        Got it!
                    </button>
                    <button class="donation-btn primary" onclick="closeAboutModal(); showDonationInfo()">
                        Support the Vision
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', aboutHTML);
}

function closeAboutModal() {
    const modal = document.getElementById('aboutModal');
    if (modal) {
        modal.remove();
    }
}