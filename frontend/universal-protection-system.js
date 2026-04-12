// ============================================================
// EliteGets 全版本防盜版和防破解系統
// 適用於: Advance (Free) | Pro ($490) | Ultimate ($1490)
// ============================================================

'use strict';

class UniversalProtectionSystem {
    constructor(versionType = 'advance') {
        this.versionType = versionType; // 'advance', 'pro', 'ultimate'
        this.licenseKey = null;
        this.deviceFingerprint = null;
        this.licenseServer = 'https://license.elitegets.com';
        this.protectionLevel = this.getProtectionLevel(versionType);
        this.verificationAttempts = 0;
        this.maxAttempts = 3;
        this.isVerified = false;
        
        // 根據版本設置保護參數
        this.config = {
            advance: {
                offlineGracePeriod: 7 * 24 * 60 * 60 * 1000, // 7 天
                verificationInterval: 48 * 60 * 60 * 1000, // 48 小時
                protectionLevel: 'basic',
                enforceMFA: false,
                encryptionStrength: 'AES-128'
            },
            pro: {
                offlineGracePeriod: 14 * 24 * 60 * 60 * 1000, // 14 天
                verificationInterval: 24 * 60 * 60 * 1000, // 24 小時
                protectionLevel: 'standard',
                enforceMFA: false,
                encryptionStrength: 'AES-192'
            },
            ultimate: {
                offlineGracePeriod: 30 * 24 * 60 * 60 * 1000, // 30 天
                verificationInterval: 12 * 60 * 60 * 1000, // 12 小時
                protectionLevel: 'enterprise',
                enforceMFA: true,
                encryptionStrength: 'AES-256'
            }
        };
    }

    /**
     * 獲取版本的保護級別
     */
    getProtectionLevel(version) {
        const levels = {
            advance: 1,
            pro: 2,
            ultimate: 3
        };
        return levels[version] || 1;
    }

    /**
     * 初始化保護系統
     */
    async initialize() {
        console.log(`🔐 正在初始化 ${this.versionType.toUpperCase()} 版本保護系統...`);

        // 第 1 步：啟用反調試
        this.enableAntiDebug();

        // 第 2 步：生成設備指紋
        this.deviceFingerprint = await this.generateDeviceFingerprint();

        // 第 3 步：獲取許可證
        const licenseKey = this.getLicenseKey();
        if (!licenseKey) {
            console.error('❌ 未找到許可證');
            this.disableFeatures('no_license');
            return false;
        }

        this.licenseKey = licenseKey;

        // 第 4 步：驗證許可證
        const result = await this.verifyLicense();

        if (!result.valid) {
            console.error('❌ 許可證驗證失敗:', result.reason);
            this.disableFeatures('verification_failed');
            return false;
        }

        this.isVerified = true;

        // 第 5 步：啟用功能保護
        this.enableFeatureProtection();

        // 第 6 步：啟動定期驗證
        this.startPeriodicVerification();

        console.log(`✅ ${this.versionType.toUpperCase()} 版本已激活並受保護`);
        return true;
    }

    /**
     * ============================================
     * 反調試系統（所有版本）
     * ============================================
     */

    enableAntiDebug() {
        // 禁用控制台
        this.disableConsole();

        // 禁用開發者工具快捷鍵
        this.disableDevTools();

        // 檢測虛擬機
        if (this.detectVirtualMachine()) {
            console.log('⚠️ 檢測到虛擬環境，啟用增強防護');
        }

        // 檢測代理/調試工具
        if (this.detectDebugTools()) {
            console.log('⚠️ 檢測到開發者工具');
        }

        // 防止 eval 執行
        this.blockEval();

        // 防止代碼注入
        this.preventCodeInjection();
    }

    disableConsole() {
        const noop = () => {};
        window.console = {
            log: noop,
            error: noop,
            warn: noop,
            info: noop,
            debug: noop,
            trace: noop,
            table: noop
        };

        // 防止 console 被重新分配
        Object.defineProperty(window, 'console', {
            get: () => {
                this.reportSecurityEvent('console_access_attempt');
                return {
                    log: noop,
                    error: noop,
                    warn: noop,
                    info: noop,
                    debug: noop
                };
            }
        });
    }

    disableDevTools() {
        document.addEventListener('keydown', (event) => {
            // F12
            if (event.key === 'F12') {
                event.preventDefault();
                this.reportSecurityEvent('devtools_f12');
                return false;
            }

            // Ctrl+Shift+I
            if (event.ctrlKey && event.shiftKey && event.key === 'I') {
                event.preventDefault();
                this.reportSecurityEvent('devtools_ctrl_shift_i');
                return false;
            }

            // Ctrl+Shift+J
            if (event.ctrlKey && event.shiftKey && event.key === 'J') {
                event.preventDefault();
                this.reportSecurityEvent('devtools_ctrl_shift_j');
                return false;
            }

            // Ctrl+Shift+C
            if (event.ctrlKey && event.shiftKey && event.key === 'C') {
                event.preventDefault();
                this.reportSecurityEvent('devtools_ctrl_shift_c');
                return false;
            }

            // Ctrl+Shift+K
            if (event.ctrlKey && event.shiftKey && event.key === 'K') {
                event.preventDefault();
                this.reportSecurityEvent('devtools_ctrl_shift_k');
                return false;
            }
        });

        // 禁用右鍵菜單
        document.addEventListener('contextmenu', (event) => {
            event.preventDefault();
            return false;
        });

        // 禁用複製
        document.addEventListener('copy', (event) => {
            event.preventDefault();
            return false;
        });

        // 禁用剪切
        document.addEventListener('cut', (event) => {
            event.preventDefault();
            return false;
        });

        // 禁用拖放
        document.addEventListener('dragstart', (event) => {
            event.preventDefault();
            return false;
        });
    }

    detectVirtualMachine() {
        const userAgent = navigator.userAgent.toLowerCase();
        const vmIndicators = [
            'virtualbox', 'vmware', 'kvm', 'qemu', 'xen', 'hyperv',
            'docker', 'wine', 'virtualpc', 'parallels', 'vbox'
        ];
        return vmIndicators.some(vm => userAgent.includes(vm));
    }

    detectDebugTools() {
        // 檢測大小
        const threshold = 160;
        if (window.outerHeight - window.innerHeight > threshold ||
            window.outerWidth - window.innerWidth > threshold) {
            return true;
        }

        // 檢測 debugger
        try {
            const start = performance.now();
            debugger;
            const end = performance.now();
            if (end - start > 100) {
                return true;
            }
        } catch (e) {}

        return false;
    }

    blockEval() {
        window.eval = new Proxy(eval, {
            apply() {
                this.reportSecurityEvent('eval_attempt');
                throw new Error('eval 已被禁用');
            }
        });

        window.Function = new Proxy(Function, {
            construct() {
                this.reportSecurityEvent('function_constructor_attempt');
                throw new Error('Function 構造函數已被禁用');
            }
        });
    }

    preventCodeInjection() {
        // 監控 DOM 修改
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.tagName === 'SCRIPT' && !node.hasAttribute('data-trusted')) {
                            console.error('🚨 檢測到未授權的腳本注入');
                            this.reportSecurityEvent('script_injection_detected');
                            node.remove();
                        }
                    });
                }
            });
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    }

    /**
     * ============================================
     * 設備指紋系統（所有版本）
     * ============================================
     */

    async generateDeviceFingerprint() {
        const components = {
            // 基礎指紋（所有版本）
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            localStorage: this.getStorageId(),

            // 增強指紋（Pro 及以上）
            ...(this.protectionLevel >= 2 && {
                canvas: await this.getCanvasFingerprint(),
                webgl: this.getWebGLFingerprint(),
                fonts: this.getFontFingerprint()
            }),

            // 企業指紋（Ultimate）
            ...(this.protectionLevel >= 3 && {
                hardwareConcurrency: navigator.hardwareConcurrency,
                deviceMemory: navigator.deviceMemory,
                maxTouchPoints: navigator.maxTouchPoints,
                screenResolution: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth
            })
        };

        const fingerprintString = JSON.stringify(components);
        return await this.sha256(fingerprintString);
    }

    getStorageId() {
        let storageId = localStorage.getItem('__elitegets_device_id');
        if (!storageId) {
            storageId = 'dev_' + Math.random().toString(36).substr(2, 16);
            try {
                localStorage.setItem('__elitegets_device_id', storageId);
            } catch (e) {}
        }
        return storageId;
    }

    async getCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = 280;
            canvas.height = 60;
            const ctx = canvas.getContext('2d');

            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('EliteGets', 2, 15);

            return await this.sha256(canvas.toDataURL());
        } catch (e) {
            return 'canvas_unavailable';
        }
    }

    getWebGLFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
            const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            return `${vendor}|${renderer}`;
        } catch (e) {
            return 'webgl_unavailable';
        }
    }

    getFontFingerprint() {
        const fonts = ['Arial', 'Verdana', 'Georgia', 'Times New Roman'];
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        let fontStr = '';

        fonts.forEach(font => {
            ctx.font = `14px "${font}", monospace`;
            fontStr += ctx.measureText('EliteGets').width;
        });

        return fontStr;
    }

    /**
     * ============================================
     * 許可證驗證系統（所有版本）
     * ============================================
     */

    getLicenseKey() {
        // 優先級：環境變量 > localStorage > HTML data 屬性
        return window.ELITEGETS_LICENSE_KEY ||
               localStorage.getItem('__elitegets_license_key') ||
               document.documentElement.getAttribute('data-license-key') ||
               null;
    }

    async verifyLicense() {
        try {
            // 嘗試線上驗證
            const result = await this.verifyOnline();

            if (result.valid) {
                this.storeVerificationToken(result.token);
                return { valid: true, mode: 'online' };
            } else {
                // 降級到離線模式
                return await this.verifyOffline();
            }
        } catch (error) {
            console.warn('線上驗證失敗，使用離線模式');
            return await this.verifyOffline();
        }
    }

    async verifyOnline() {
        const request = {
            licenseKey: this.licenseKey,
            deviceFingerprint: this.deviceFingerprint,
            version: this.versionType,
            timestamp: Date.now(),
            signature: await this.sha256(
                this.licenseKey + this.deviceFingerprint + Date.now()
            )
        };

        try {
            const response = await fetch(`${this.licenseServer}/api/v2/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request),
                timeout: 30000
            });

            if (!response.ok) {
                throw new Error('Server error');
            }

            const data = await response.json();
            return {
                valid: data.valid,
                token: data.token,
                reason: data.reason
            };
        } catch (error) {
            throw error;
        }
    }

    async verifyOffline() {
        const token = this.getStoredToken();

        if (!token) {
            return { valid: false, reason: 'no_offline_token' };
        }

        try {
            const tokenData = JSON.parse(atob(token.data));

            // 檢查過期
            if (Date.now() > tokenData.expiryTime) {
                return { valid: false, reason: 'token_expired' };
            }

            // 驗證設備指紋
            if (this.deviceFingerprint !== tokenData.deviceFingerprint) {
                return { valid: false, reason: 'fingerprint_mismatch' };
            }

            return { valid: true, mode: 'offline' };
        } catch (e) {
            return { valid: false, reason: 'invalid_token' };
        }
    }

    storeVerificationToken(token) {
        const config = this.config[this.versionType];
        const expiryTime = Date.now() + config.offlineGracePeriod;

        const tokenData = {
            token: token,
            deviceFingerprint: this.deviceFingerprint,
            expiryTime: expiryTime,
            version: this.versionType
        };

        const encrypted = {
            data: btoa(JSON.stringify(tokenData)),
            signature: this.hashString(JSON.stringify(tokenData))
        };

        try {
            localStorage.setItem('__elitegets_token', JSON.stringify(encrypted));
        } catch (e) {
            console.warn('Token storage failed');
        }
    }

    getStoredToken() {
        try {
            return JSON.parse(localStorage.getItem('__elitegets_token'));
        } catch (e) {
            return null;
        }
    }

    /**
     * ============================================
     * 功能保護系統（所有版本）
     * ============================================
     */

    enableFeatureProtection() {
        // 標記受保護的功能
        document.querySelectorAll('[data-protected]').forEach(el => {
            el.style.visibility = 'visible';
            el.setAttribute('data-protected-verified', 'true');
        });

        // 監控受保護內容的訪問
        this.monitorProtectedAccess();
    }

    monitorProtectedAccess() {
        // 監控 API 調用
        this.interceptAPICalls();

        // 監控數據訪問
        this.interceptDataAccess();

        // 監控文件下載
        this.interceptDownloads();
    }

    interceptAPICalls() {
        const originalFetch = window.fetch;

        window.fetch = function(...args) {
            const [url] = args;

            // 記錄所有 API 調用
            if (url && typeof url === 'string' && url.includes('/api')) {
                console.log(`📡 API 調用: ${url}`);
            }

            return originalFetch.apply(this, args);
        };
    }

    interceptDataAccess() {
        // 監控 localStorage 訪問
        const originalSetItem = Storage.prototype.setItem;
        const originalGetItem = Storage.prototype.getItem;

        Storage.prototype.setItem = function(key, value) {
            if (!key.startsWith('__elitegets')) {
                console.log(`💾 數據存儲: ${key}`);
            }
            return originalSetItem.apply(this, arguments);
        };

        Storage.prototype.getItem = function(key) {
            if (!key.startsWith('__elitegets')) {
                console.log(`📖 數據讀取: ${key}`);
            }
            return originalGetItem.apply(this, arguments);
        };
    }

    interceptDownloads() {
        document.addEventListener('click', (event) => {
            const target = event.target.closest('a[download]');
            if (target) {
                if (!this.isVerified) {
                    event.preventDefault();
                    console.error('❌ 功能未解鎖');
                    this.showError('download_not_allowed');
                    return false;
                }
                console.log(`📥 下載: ${target.href}`);
            }
        });
    }

    /**
     * ============================================
     * 定期驗證（所有版本）
     * ============================================
     */

    startPeriodicVerification() {
        const config = this.config[this.versionType];

        // 定期重新驗證
        setInterval(async () => {
            const result = await this.verifyLicense();
            if (!result.valid) {
                console.error('❌ 定期驗證失敗');
                this.disableFeatures('periodic_verification_failed');
            }
        }, config.verificationInterval);

        // 定期檢查調試工具（Ultimate）
        if (this.protectionLevel >= 3) {
            setInterval(() => {
                if (this.detectDebugTools()) {
                    this.reportSecurityEvent('debug_tools_detected');
                }
            }, 5 * 60 * 1000); // 每 5 分鐘
        }
    }

    /**
     * ============================================
     * 錯誤處理和禁用（所有版本）
     * ============================================
     */

    disableFeatures(reason) {
        console.error(`❌ 功能已禁用: ${reason}`);

        // 隱藏受保護的功能
        document.querySelectorAll('[data-protected]').forEach(el => {
            el.style.visibility = 'hidden';
            el.style.opacity = '0.3';
            el.style.pointerEvents = 'none';
        });

        // 顯示錯誤消息
        this.showError(reason);

        // 記錄安全事件
        this.reportSecurityEvent('features_disabled', { reason });
    }

    showError(reason) {
        const errorMessages = {
            no_license: '❌ 未找到許可證',
            verification_failed: '❌ 許可證驗證失敗',
            periodic_verification_failed: '❌ 定期驗證失敗',
            download_not_allowed: '❌ 功能未解鎖'
        };

        const message = errorMessages[reason] || '❌ 許可證驗證失敗';

        const banner = document.createElement('div');
        banner.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #ff6b6b;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
            z-index: 10000;
        `;
        banner.textContent = message;
        document.body.insertBefore(banner, document.body.firstChild);
    }

    /**
     * ============================================
     * 安全事件報告（所有版本）
     * ============================================
     */

    async reportSecurityEvent(eventType, details = {}) {
        try {
            await fetch(`${this.licenseServer}/api/v2/report-event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    eventType: eventType,
                    version: this.versionType,
                    deviceFingerprint: this.deviceFingerprint,
                    timestamp: Date.now(),
                    details: details
                })
            });
        } catch (e) {
            // 靜默失敗
        }
    }

    /**
     * ============================================
     * 加密和哈希（所有版本）
     * ============================================
     */

    async sha256(message) {
        const msgBuffer = new TextEncoder().encode(message);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(16);
    }
}

// ============================================================
// 全球初始化函數
// ============================================================

async function initializeEliteGetsProtection(versionType = 'advance') {
    window.EliteGetsProtection = new UniversalProtectionSystem(versionType);
    return await window.EliteGetsProtection.initialize();
}

// 導出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UniversalProtectionSystem, initializeEliteGetsProtection };
}

// 使用示例：
// await initializeEliteGetsProtection('advance');   // Advance 版本
// await initializeEliteGetsProtection('pro');       // Pro 版本
// await initializeEliteGetsProtection('ultimate');  // Ultimate 版本
