/**
 * Metamask Web3 Authentication
 * Handles connection, message signing, and authentication with backend
 */

// API base URL
const API_BASE = '';

// Supported networks configuration
const SUPPORTED_NETWORKS = {
    1: {
        chainId: '0x1',
        chainName: 'Ethereum Mainnet',
        nativeCurrency: {
            name: 'Ether',
            symbol: 'ETH',
            decimals: 18
        },
        rpcUrls: ['https://mainnet.infura.io/v3/'],
        blockExplorerUrls: ['https://etherscan.io']
    }
};

// State management
let walletAddress = null;
let isAuthenticated = false;
let currentChainId = null;

// DOM elements
const statusEl = document.getElementById('status');
const notConnectedEl = document.getElementById('not-connected');
const connectedEl = document.getElementById('connected');
const connectBtn = document.getElementById('connect-btn');
const disconnectBtn = document.getElementById('disconnect-btn');
const walletAddressEl = document.getElementById('wallet-address');
const authStatusEl = document.getElementById('auth-status');
let messageInput, signBtn, signatureResult, signatureValue;
let currentNetworkNameEl, currentChainIdEl, networkBadgeEl, networkSelectorEl;

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
    statusEl.classList.remove('hidden');
    
    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusEl.classList.add('hidden');
        }, 3000);
    }
}

/**
 * Hide status message
 */
function hideStatus() {
    statusEl.classList.add('hidden');
}

/**
 * Check if Metamask is installed
 */
function checkMetamask() {
    if (typeof window.ethereum === 'undefined') {
        showStatus('Metamask is not installed. Please install Metamask to continue.', 'error');
        connectBtn.disabled = true;
        return false;
    }
    return true;
}

/**
 * Get current chain ID from MetaMask
 */
async function getCurrentChainId() {
    try {
        const chainId = await window.ethereum.request({
            method: 'eth_chainId'
        });
        return parseInt(chainId, 16);
    } catch (error) {
        console.error('Error getting chain ID:', error);
        return null;
    }
}

/**
 * Get network name by chain ID
 */
function getNetworkName(chainId) {
    const network = SUPPORTED_NETWORKS[chainId];
    return network ? network.chainName : `Unknown Network (${chainId})`;
}

/**
 * Check if network is supported
 */
function isNetworkSupported(chainId) {
    return chainId in SUPPORTED_NETWORKS;
}

/**
 * Switch to a specific network
 */
async function switchNetwork(chainId) {
    if (!window.ethereum) {
        showStatus('MetaMask is not installed', 'error');
        return;
    }

    const network = SUPPORTED_NETWORKS[chainId];
    if (!network) {
        showStatus('Network not supported', 'error');
        return;
    }

    try {
        showStatus(`Switching to ${network.chainName}...`, 'info');
        
        await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: network.chainId }]
        });
        
        // Update current chain ID
        currentChainId = chainId;
        updateNetworkUI();
        showStatus(`Switched to ${network.chainName}`, 'success');
        
    } catch (error) {
        // If the chain hasn't been added to MetaMask, add it
        if (error.code === 4902) {
            try {
                await window.ethereum.request({
                    method: 'wallet_addEthereumChain',
                    params: [network]
                });
                currentChainId = chainId;
                updateNetworkUI();
                showStatus(`Added and switched to ${network.chainName}`, 'success');
            } catch (addError) {
                console.error('Error adding chain:', addError);
                showStatus(`Error adding network: ${addError.message}`, 'error');
            }
        } else if (error.code === 4001) {
            showStatus('Network switch was rejected', 'error');
        } else {
            console.error('Error switching network:', error);
            showStatus(`Error switching network: ${error.message}`, 'error');
        }
    }
}

/**
 * Update network UI
 */
function updateNetworkUI() {
    if (!currentNetworkNameEl || !currentChainIdEl || !networkBadgeEl || !networkSelectorEl) {
        return;
    }

    if (currentChainId === null) {
        currentNetworkNameEl.textContent = '-';
        currentChainIdEl.textContent = '-';
        networkBadgeEl.classList.remove('unsupported');
        return;
    }

    const networkName = getNetworkName(currentChainId);
    const isSupported = isNetworkSupported(currentChainId);

    currentNetworkNameEl.textContent = networkName;
    currentChainIdEl.textContent = currentChainId;
    
    if (isSupported) {
        networkBadgeEl.classList.remove('unsupported');
    } else {
        networkBadgeEl.classList.add('unsupported');
    }

    // Update network selector buttons
    networkSelectorEl.innerHTML = '';
    Object.keys(SUPPORTED_NETWORKS).forEach(chainId => {
        const network = SUPPORTED_NETWORKS[chainId];
        const btn = document.createElement('button');
        btn.className = `network-btn ${parseInt(chainId) === currentChainId ? 'active' : ''}`;
        btn.innerHTML = `
            <span class="network-name">${network.chainName}</span>
            <span class="network-chain-id">Chain ID: ${chainId}</span>
        `;
        btn.addEventListener('click', () => switchNetwork(parseInt(chainId)));
        networkSelectorEl.appendChild(btn);
    });
}

/**
 * Initialize network information
 */
async function initNetwork() {
    if (!window.ethereum) {
        return;
    }

    try {
        currentChainId = await getCurrentChainId();
        updateNetworkUI();
    } catch (error) {
        console.error('Error initializing network:', error);
    }
}

/**
 * Request account access from Metamask
 */
async function requestAccountAccess() {
    try {
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });
        return accounts[0];
    } catch (error) {
        if (error.code === 4001) {
            showStatus('Please connect to Metamask to continue.', 'error');
        } else {
            showStatus(`Error connecting to Metamask: ${error.message}`, 'error');
        }
        throw error;
    }
}

/**
 * Get nonce from backend
 */
async function getNonce(address) {
    try {
        const response = await fetch(`${API_BASE}/auth/nonce`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ wallet_address: address })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get nonce');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        showStatus(`Error getting nonce: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Sign message with Metamask
 */
async function signMessage(message, address) {
    try {
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [message, address]
        });
        return signature;
    } catch (error) {
        if (error.code === 4001) {
            showStatus('Message signature was rejected.', 'error');
        } else {
            showStatus(`Error signing message: ${error.message}`, 'error');
        }
        throw error;
    }
}

/**
 * Verify signature and get JWT token
 */
async function verifySignature(address, signature, message) {
    try {
        const response = await fetch(`${API_BASE}/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                wallet_address: address,
                signature: signature,
                message: message
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to verify signature');
        }

        const data = await response.json();
        return data.token;
    } catch (error) {
        showStatus(`Error verifying signature: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Store token in cookie
 */
function storeToken(token) {
    // Set cookie with token (expires in 24 hours)
    const expires = new Date();
    expires.setTime(expires.getTime() + 24 * 60 * 60 * 1000);
    document.cookie = `auth_token=${token}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
}

/**
 * Remove token from cookie
 */
function removeToken() {
    document.cookie = 'auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
}

/**
 * Connect to Metamask and authenticate
 */
async function connect() {
    if (!checkMetamask()) {
        return;
    }

    try {
        connectBtn.disabled = true;
        connectBtn.innerHTML = '<span class="loading"></span>Connecting...';
        hideStatus();

        // Request account access
        const address = await requestAccountAccess();
        walletAddress = address;

        // Get current chain ID
        currentChainId = await getCurrentChainId();
        updateNetworkUI();

        showStatus('Getting authentication challenge...', 'info');

        // Get nonce from backend
        const { nonce, message } = await getNonce(address);

        showStatus('Please sign the message in Metamask...', 'info');

        // Sign message with Metamask
        const signature = await signMessage(message, address);

        showStatus('Verifying signature...', 'info');

        // Verify signature and get token
        const token = await verifySignature(address, signature, message);

        // Store token
        storeToken(token);
        isAuthenticated = true;

        // Update UI
        updateUI();
        showStatus('Successfully authenticated!', 'success');

    } catch (error) {
        console.error('Authentication error:', error);
        walletAddress = null;
        isAuthenticated = false;
    } finally {
        connectBtn.disabled = false;
        connectBtn.innerHTML = 'Connect Metamask';
    }
}

/**
 * Disconnect wallet
 */
function disconnect() {
    walletAddress = null;
    isAuthenticated = false;
    removeToken();
    updateUI();
    showStatus('Disconnected successfully', 'info');
    // Clear signature result
    signatureResult.classList.add('hidden');
    messageInput.value = '';
}

/**
 * Sign arbitrary text with Metamask
 */
async function signText() {
    if (!isAuthenticated) {
        showStatus('Please connect and authenticate first', 'error');
        return;
    }

    if (!messageInput || !signBtn || !signatureValue || !signatureResult) {
        console.error('Sign section elements not found');
        return;
    }

    const text = messageInput.value.trim();
    
    if (!text) {
        showStatus('Please enter some text to sign', 'error');
        return;
    }

    try {
        signBtn.disabled = true;
        signBtn.innerHTML = '<span class="loading"></span>Signing...';
        hideStatus();

        // Get current account from MetaMask
        const accounts = await window.ethereum.request({
            method: 'eth_accounts'
        });

        if (!accounts || accounts.length === 0) {
            showStatus('No account connected. Please connect MetaMask.', 'error');
            return;
        }

        const currentAddress = accounts[0];

        showStatus('Please sign the message in Metamask...', 'info');

        // Sign message with Metamask (address is optional, but we provide it for clarity)
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [text, currentAddress]
        });

        // Display signature
        signatureValue.textContent = signature;
        signatureResult.classList.remove('hidden');
        
        showStatus('Message signed successfully!', 'success');

    } catch (error) {
        console.error('Signing error:', error);
        if (error.code === 4001) {
            showStatus('Message signature was rejected.', 'error');
        } else {
            showStatus(`Error signing message: ${error.message}`, 'error');
        }
        if (signatureResult) {
            signatureResult.classList.add('hidden');
        }
    } finally {
        if (signBtn) {
            signBtn.disabled = false;
            signBtn.innerHTML = 'Sign with MetaMask';
        }
    }
}

/**
 * Update UI based on connection state
 */
function updateUI() {
    if (isAuthenticated && walletAddress) {
        notConnectedEl.classList.add('hidden');
        connectedEl.classList.remove('hidden');
        walletAddressEl.textContent = walletAddress;
        authStatusEl.textContent = 'Authenticated';
        // Update network UI when connected
        updateNetworkUI();
    } else {
        notConnectedEl.classList.remove('hidden');
        connectedEl.classList.add('hidden');
        // Clear signature result when disconnected
        if (signatureResult) {
            signatureResult.classList.add('hidden');
        }
        if (messageInput) {
            messageInput.value = '';
        }
        // Reset network info
        currentChainId = null;
        if (currentNetworkNameEl) {
            currentNetworkNameEl.textContent = '-';
        }
        if (currentChainIdEl) {
            currentChainIdEl.textContent = '-';
        }
    }
}

/**
 * Handle account changes in Metamask
 */
function setupAccountChangeListener() {
    if (window.ethereum) {
        window.ethereum.on('accountsChanged', (accounts) => {
            if (accounts.length === 0) {
                // User disconnected from Metamask
                disconnect();
            } else if (accounts[0] !== walletAddress) {
                // User switched accounts
                walletAddress = accounts[0].toLowerCase();
                if (isAuthenticated) {
                    // Re-authenticate with new account
                    connect();
                }
            }
        });

        window.ethereum.on('chainChanged', async (chainIdHex) => {
            // Update chain ID when user switches networks
            currentChainId = parseInt(chainIdHex, 16);
            updateNetworkUI();
            
            // Show notification about network change
            const networkName = getNetworkName(currentChainId);
            if (isNetworkSupported(currentChainId)) {
                showStatus(`Network changed to ${networkName}`, 'info');
            } else {
                showStatus(`Unsupported network: ${networkName}. Please switch to a supported network.`, 'error');
            }
        });
    }
}

/**
 * Check if user is already authenticated
 */
async function checkExistingAuth() {
    // Check if we have a token in cookies
    const cookies = document.cookie.split(';');
    const tokenCookie = cookies.find(c => c.trim().startsWith('auth_token='));
    
    if (tokenCookie) {
        const token = tokenCookie.split('=')[1];
        // Try to verify token with backend
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const userInfo = await response.json();
                walletAddress = userInfo.wallet_address;
                isAuthenticated = true;
                updateUI();
                return;
            }
        } catch (error) {
            console.error('Error checking auth:', error);
        }
    }

    // If no valid token, check if Metamask is already connected
    if (window.ethereum) {
        try {
            const accounts = await window.ethereum.request({
                method: 'eth_accounts'
            });
            if (accounts.length > 0) {
                walletAddress = accounts[0];
                // Don't auto-authenticate, just show connect button
            }
        } catch (error) {
            console.error('Error checking accounts:', error);
        }
    }
}

/**
 * Initialize the application
 */
async function init() {
    // Check Metamask on load
    checkMetamask();

    // Get sign section elements
    messageInput = document.getElementById('message-input');
    signBtn = document.getElementById('sign-btn');
    signatureResult = document.getElementById('signature-result');
    signatureValue = document.getElementById('signature-value');

    // Get network section elements
    currentNetworkNameEl = document.getElementById('current-network-name');
    currentChainIdEl = document.getElementById('current-chain-id');
    networkBadgeEl = document.getElementById('network-badge');
    networkSelectorEl = document.getElementById('network-selector');

    // Setup event listeners
    connectBtn.addEventListener('click', connect);
    disconnectBtn.addEventListener('click', disconnect);
    
    if (signBtn) {
        signBtn.addEventListener('click', signText);
    }
    
    // Allow signing with Enter key (Ctrl+Enter or Cmd+Enter)
    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                signText();
            }
        });
    }

    // Setup Metamask event listeners
    setupAccountChangeListener();

    // Initialize network information
    await initNetwork();

    // Check for existing authentication
    await checkExistingAuth();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

