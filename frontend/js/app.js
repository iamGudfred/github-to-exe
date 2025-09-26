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

                <div class="amount-selection">
                    <h4>Select Amount</h4>
                    <div class="preset-amounts">
                        <button class="amount-btn" data-amount="5">$5</button>
                        <button class="amount-btn selected" data-amount="7">$7</button>
                        <button class="amount-btn" data-amount="10">$10</button>
                        <button class="amount-btn" data-amount="25">$25</button>
                        <button class="amount-btn" data-amount="50">$50</button>
                    </div>
                    <div class="custom-amount">
                        <label for="customAmount">Custom Amount:</label>
                        <input type="number" id="customAmount" placeholder="Enter amount" min="1" step="0.01">
                    </div>
                    <div class="selected-amount">
                        Selected: $<span id="selectedAmount">7</span>
                    </div>
                </div>

                <div class="payment-methods">
                    <a href="https://x.com/iamGudfred" target="_blank" class="payment-option">
                        <div class="payment-icon"><i class="fab fa-twitter"></i></div>
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

                    <div class="payment-option disabled-payment" title="Stripe not available in Ghana - Working on U.S. entity setup">
                        <div class="payment-icon"><i class="fab fa-stripe"></i></div>
                        <span>Stripe <small>(Coming Soon)</small></span>
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

    // Add amount selection functionality
    setTimeout(() => {
        const modal = document.getElementById('donationModal');
        const amountBtns = document.querySelectorAll('.amount-btn');
        const customAmountInput = document.getElementById('customAmount');
        const selectedAmountSpan = document.getElementById('selectedAmount');

        // Handle preset amount buttons
        amountBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                amountBtns.forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                customAmountInput.value = '';
                selectedAmountSpan.textContent = btn.dataset.amount;
            });
        });

        // Handle custom amount input with robust validation
        customAmountInput.addEventListener('input', () => {
            const rawValue = customAmountInput.value.trim();
            if (!rawValue) return;

            const amount = validateAmount(rawValue);
            if (amount !== null) {
                amountBtns.forEach(b => b.classList.remove('selected'));
                selectedAmountSpan.textContent = amount.toFixed(2);
            }
        });

        // Add click-outside-to-close functionality
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
        // Clipboard copy failed, but address is shown in alert
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
                <h3>Our Story</h3>

                <div class="story-text">
                    <p>I was browsing GitHub one evening when I found this amazing Python calculator. Simple, clean, exactly what I needed. But then I hit that familiar wall: "Clone the repository, install Python, pip install requirements, python main.py..." </p>

                    <p>I just wanted to <em>use</em> the damn thing.</p>

                    <p>That's when it hit me. Millions of people discover incredible projects on GitHub every day. Useful tools, fun games, helpful utilities. But most never get to actually use them because they're not developers.</p>

                    <p>So I built this.</p>

                    <p>I’m Godfred, a passionate lifelong learner from Ghana. I've been in those shoes - wanting to use software but getting lost in technical setup. This tool solves that. Paste a GitHub URL, get a Windows executable. Simple.</p>

                    <p>Right now it works for Python projects, but here's where it gets exciting: <strong>this is going open source.</strong></p>

                    <p>I want developers from around the world to help expand this. Imagine if we could do this for any language:</p>

                    <div class="vision-list">
                        • JavaScript projects → Desktop apps<br>
                        • Go programs → Cross-platform executables<br>
                        • Rust code → Optimized binaries<br>
                        • Eventually: Web apps → Mobile apps
                    </div>

                    <p>We could bridge the gap between developers and users everywhere. Make software truly accessible.</p>

                    <p>Your support helps keep this running and proves there's demand for this vision. Whether you star the repo, share it, or contribute financially, you're part of making software more human.</p>

                    <p><strong>From Ghana to the world. Let's build something that matters.</strong></p>
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

/**
 * Validate amount input with comprehensive edge case handling
 * @param {string} input - Raw input string
 * @returns {number|null} - Validated amount or null if invalid
 */
function validateAmount(input) {
    // Remove whitespace and check for empty input
    const trimmed = input.trim();
    if (!trimmed) return null;

    // Parse as float
    const parsed = parseFloat(trimmed);

    // Check for NaN, Infinity, or negative values
    if (isNaN(parsed) || !isFinite(parsed) || parsed <= 0) {
        return null;
    }

    // Set reasonable bounds (min $0.50, max $10,000)
    const MIN_AMOUNT = 0.5;
    const MAX_AMOUNT = 10000;
    if (parsed < MIN_AMOUNT || parsed > MAX_AMOUNT) {
        return null;
    }

    // Round to cents to avoid floating point issues
    return Math.round(parsed * 100) / 100;
}

// Payment processing function
async function processPayment(method) {
    try {
        // Get selected amount with robust validation
        const selectedAmountSpan = document.getElementById('selectedAmount');
        if (!selectedAmountSpan) {
            alert('Error: Amount selection not found');
            return;
        }

        const selectedAmount = validateAmount(selectedAmountSpan.textContent);

        if (selectedAmount === null) {
            alert('Please select or enter a valid amount between $0.50 and $10,000');
            return;
        }

        closeDonationModal(); // Close current modal

        const response = await fetch(`/api/payment/${method}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                amount: selectedAmount,
                email: 'donor@example.com' // For Paystack, you might want to ask for email
            })
        });

        const data = await response.json();

        if (!response.ok) {
            // Show specific error from server
            throw new Error(data.error || `Payment setup failed: ${response.status}`);
        }

        if (method === 'stripe' && data.checkout_url) {
            window.open(data.checkout_url, '_blank');
        } else if (method === 'paypal' && data.approval_url) {
            window.open(data.approval_url, '_blank');
        } else if (method === 'paystack' && data.authorization_url) {
            window.open(data.authorization_url, '_blank');
        } else {
            throw new Error('Payment URL not received from server');
        }

    } catch (error) {
        console.error('Payment error:', error);

        let errorMessage = 'Payment setup failed. ';
        if (error.message.includes('not configured')) {
            errorMessage += 'Payment gateway is not configured yet. Please try Buy Me a Coffee or Bitcoin instead.';
        } else {
            errorMessage += 'Please try again or use an alternative method.';
        }

        alert(errorMessage);
    }
}