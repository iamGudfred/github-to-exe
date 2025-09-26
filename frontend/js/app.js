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
                <p>Choose your preferred way to help keep this tool free and improve build capabilities.</p>

                <div class="payment-methods">
                    <a href="https://x.com/iamGudfred" target="_blank" class="payment-option">
                        <div class="payment-icon"><i class="fab fa-x-twitter"></i></div>
                        <span>X (Twitter) Tips</span>
                    </a>

                    <a href="https://buymeacoffee.com/gudfred" target="_blank" class="payment-option">
                        <div class="payment-icon"><i class="fas fa-coffee"></i></div>
                        <span>Buy Me a Coffee</span>
                    </a>

                    <div class="payment-option" onclick="processPayment('paypal')">
                        <div class="payment-icon"><i class="fab fa-paypal"></i></div>
                        <span>PayPal</span>
                    </div>

                    <div class="payment-option" onclick="processPayment('stripe')">
                        <div class="payment-icon"><i class="fab fa-stripe"></i></div>
                        <span>Stripe</span>
                    </div>

                    <div class="payment-option bitcoin-option" onclick="showBitcoinAddress()">
                        <div class="payment-icon"><i class="fab fa-bitcoin"></i></div>
                        <span>Bitcoin</span>
                    </div>
                </div>

                <div class="donation-goal">
                    <p><strong>Goal:</strong> Upgrade to paid hosting ($7/month) for faster, more reliable builds</p>
                </div>

                <div class="donation-actions">
                    <button class="donation-btn secondary" onclick="closeDonationModal()">
                        Close
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', donationHTML);

    // Add click-outside-to-close functionality
    setTimeout(() => {
        const modal = document.getElementById('donationModal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeDonationModal();
            }
        });
    }, 100);
}

function showBitcoinAddress() {
    alert('Bitcoin Address:\\n1H1KFHWxAkySDyuSR9hTaVymnzgE5G9yDc\\n\\nAddress copied to clipboard!');
    navigator.clipboard.writeText('1H1KFHWxAkySDyuSR9hTaVymnzgE5G9yDc').catch(() => {
        console.log('Clipboard copy failed, but address is shown in alert');
    });
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

    // Add click-outside-to-close functionality
    setTimeout(() => {
        const modal = document.getElementById('errorModal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeErrorModal();
            }
        });
    }, 100);
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
                    <p>Every day, millions of people—non-tech enthusiasts included—stumble upon amazing projects on GitHub: calculators, games, tools, and more. But they hit a wall. Complex setups, command lines, and software dependencies leave them frustrated, unable to enjoy what they find.</p>
                    <p>A tweet summed it up perfectly: "Why can't I just download and run this?"</p>
                </div>

                <div class="story-section">
                    <h4>Our Journey</h4>
                    <p>This tool was born from that frustration. As Godfred Prebbie Mensah, a self-taught learner from Ghana, I felt the same struggle. I wanted to create a simple solution to turn any GitHub project into a ready-to-run file with a single click.</p>
                    <p>It started with Python, but the dream is bigger.</p>
                </div>

                <div class="story-section">
                    <h4>Our Vision</h4>
                    <p>We're making software accessible to everyone, no matter their tech skills. This is just the beginning. We're opening this project to the world, inviting global engineers and developers to collaborate.</p>
                    <p><strong>Our roadmap includes:</strong></p>
                    <ul style="text-align: left; margin: 10px 0;">
                        <li>Support for macOS (.app files) and Linux executables</li>
                        <li>Converting projects in JavaScript, Go, Rust, and more into executables</li>
                        <li>Eventually, mobile app generation for wider reach</li>
                    </ul>
                    <p>This will be open source, empowering a global community to expand and improve it.</p>
                </div>

                <div class="story-section">
                    <h4>Join the Movement</h4>
                    <p>Every star on GitHub, share, or donation brings us closer to this vision. Together, we can make software accessible to everyone, everywhere.</p>
                    <p>From Ghana to the world—let's build something amazing.</p>
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

    // Add click-outside-to-close functionality
    setTimeout(() => {
        const modal = document.getElementById('aboutModal');
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAboutModal();
            }
        });
    }, 100);
}

function closeAboutModal() {
    const modal = document.getElementById('aboutModal');
    if (modal) {
        modal.remove();
    }
}

// Payment processing function
async function processPayment(method) {
    try {
        closeDonationModal(); // Close current modal

        const response = await fetch(`/api/payment/${method}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                amount: 7.00,
                email: 'donor@example.com' // For Paystack, you might want to ask for email
            })
        });

        if (!response.ok) {
            throw new Error(`Payment setup failed: ${response.status}`);
        }

        const data = await response.json();

        if (method === 'stripe' && data.checkout_url) {
            window.open(data.checkout_url, '_blank');
        } else if (method === 'paypal' && data.approval_url) {
            window.open(data.approval_url, '_blank');
        } else if (method === 'paystack' && data.authorization_url) {
            window.open(data.authorization_url, '_blank');
        } else {
            throw new Error('Payment URL not received');
        }

    } catch (error) {
        console.error('Payment error:', error);
        alert('Payment setup failed. Please try again or use an alternative method.');
    }
}