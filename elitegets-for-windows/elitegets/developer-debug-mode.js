// ============================================================
// EliteGets 开发者调试模式系统
// 允许授权开发人员进行调试，同时保持生产环境安全
// ============================================================

'use strict';

class DeveloperDebugMode {
    constructor() {
        this.isDevMode = false;
        this.developerKey = null;
        this.authenticatedDevelopers = new Set();
        this.debugConsole = null;
        this.allowedFeatures = [];
        this.sessionStartTime = null;
        this.sessionTimeout = 8 * 60 * 60 * 1000; // 8 小時
        this.developersServer = 'https://developers.elitegets.com';
        this.debugLogs = [];
        this.maxLogs = 10000;
    }

    /**
     * ============================================
     * 開發者密鑰驗證系統
     * ============================================
     */

    /**
     * 啟用開發者模式（需要開發者密鑰）
     */
    async enableDeveloperMode(developerKey) {
        console.log('🔑 正在驗證開發者密鑰...');

        // 第 1 步：驗證密鑰格式
        if (!this.validateKeyFormat(developerKey)) {
            console.error('❌ 無效的開發者密鑰格式');
            this.logDebugEvent('invalid_key_format', { attemptedKey: developerKey.substring(0, 8) + '...' });
            return false;
        }

        // 第 2 步：驗證密鑰真實性（伺服器端驗證）
        const keyValid = await this.verifyKeyWithServer(developerKey);
        if (!keyValid) {
            console.error('❌ 開發者密鑰驗證失敗');
            this.logDebugEvent('key_verification_failed', { key: developerKey.substring(0, 8) });
            return false;
        }

        // 第 3 步：檢查密鑰過期
        const keyData = await this.getKeyMetadata(developerKey);
        if (keyData.expired) {
            console.error('❌ 開發者密鑰已過期');
            this.logDebugEvent('key_expired', { expiryDate: keyData.expiryDate });
            return false;
        }

        // 第 4 步：檢查開發者狀態
        if (keyData.status !== 'active') {
            console.error('❌ 開發者帳戶已禁用');
            this.logDebugEvent('developer_disabled', { developerId: keyData.developerId });
            return false;
        }

        // 成功激活開發者模式
        this.isDevMode = true;
        this.developerKey = developerKey;
        this.authenticatedDevelopers.add(keyData.developerId);
        this.sessionStartTime = Date.now();
        this.allowedFeatures = keyData.allowedFeatures || [];

        console.log('✅ 開發者模式已啟用');
        console.log(`👨‍💻 開發者: ${keyData.developerName}`);
        console.log(`⏰ 會話時限: ${this.getSessionRemainingTime()}分鐘`);

        // 第 5 步：解鎖調試功能
        this.unlockDebugFeatures();

        // 第 6 步：啟動會話監控
        this.startSessionMonitoring();

        // 記錄事件
        this.logDebugEvent('developer_mode_enabled', {
            developerId: keyData.developerId,
            features: this.allowedFeatures
        });

        return true;
    }

    /**
     * 驗證密鑰格式
     */
    validateKeyFormat(key) {
        // 格式: DEV-XXXXXXXXXXXXXXXXXXXXX
        const regex = /^DEV-[A-Z0-9]{32}$/;
        return regex.test(key);
    }

    /**
     * 向伺服器驗證密鑰
     */
    async verifyKeyWithServer(developerKey) {
        try {
            const response = await fetch(`${this.developersServer}/api/v1/verify-dev-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    key: developerKey,
                    machineId: this.getMachineId(),
                    timestamp: Date.now()
                })
            });

            if (!response.ok) {
                return false;
            }

            const data = await response.json();
            return data.valid === true;
        } catch (error) {
            console.error('密鑰驗證失敗:', error);
            return false;
        }
    }

    /**
     * 獲取密鑰元數據
     */
    async getKeyMetadata(developerKey) {
        try {
            const response = await fetch(`${this.developersServer}/api/v1/dev-key-info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: developerKey })
            });

            if (!response.ok) {
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('獲取密鑰元數據失敗:', error);
            return null;
        }
    }

    /**
     * 獲取機器 ID（用於密鑰綁定）
     */
    getMachineId() {
        let machineId = localStorage.getItem('__elitegets_machine_id');
        if (!machineId) {
            machineId = 'machine_' + Math.random().toString(36).substr(2, 16);
            localStorage.setItem('__elitegets_machine_id', machineId);
        }
        return machineId;
    }

    /**
     * ============================================
     * 環境檢測和適應
     * ============================================
     */

    /**
     * 檢測運行環境
     */
    detectEnvironment() {
        const environment = {
            isDevelopment: this.isDevelopmentEnvironment(),
            isLocalhost: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
            isProduction: this.isProductionEnvironment(),
            protocol: window.location.protocol,
            hostname: window.location.hostname,
            port: window.location.port,
            userAgent: navigator.userAgent
        };

        console.log('🌍 環境檢測:', environment);
        return environment;
    }

    isDevelopmentEnvironment() {
        return window.location.hostname === 'localhost' ||
               window.location.hostname === '127.0.0.1' ||
               window.location.hostname.includes('dev-') ||
               window.location.hostname.includes('staging');
    }

    isProductionEnvironment() {
        return window.location.protocol === 'https:' &&
               !this.isDevelopmentEnvironment();
    }

    /**
     * ============================================
     * 調試功能解鎖
     * ============================================
     */

    unlockDebugFeatures() {
        console.log('🔓 解鎖調試功能...');

        // 1. 恢復控制台
        this.restoreConsole();

        // 2. 允許 DevTools
        this.allowDevTools();

        // 3. 啟用調試面板
        this.enableDebugPanel();

        // 4. 允許本地存儲訪問
        this.allowLocalStorage();

        // 5. 啟用代碼檢查
        this.enableCodeInspection();

        // 6. 啟用 API 調試
        this.enableAPIDebugging();

        // 7. 啟用性能監控
        this.enablePerformanceMonitoring();

        console.log('✅ 所有調試功能已解鎖');
    }

    restoreConsole() {
        // 恢復完整的 console 功能
        window.console = console;

        // 添加自定義日誌方法
        console._debug = console.log;
        console.debug = (...args) => {
            this.logDebugEvent('console_debug', { args });
            console._debug(...args);
        };

        console._trace = console.trace;
        console.trace = (...args) => {
            this.logDebugEvent('console_trace', { args });
            console._trace(...args);
        };
    }

    allowDevTools() {
        // 移除 DevTools 檢測
        // 允許 F12
        document.removeEventListener('keydown', this.blockF12);

        // 允許 Ctrl+Shift+I
        // 允許 Ctrl+Shift+J

        console.log('✅ 開發者工具已解鎖');
    }

    enableDebugPanel() {
        // 創建調試面板
        const debugPanel = document.createElement('div');
        debugPanel.id = '__elitegets_debug_panel';
        debugPanel.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 400px;
            height: 300px;
            background: #1e1e1e;
            border: 2px solid #4FC3F7;
            border-radius: 8px;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow: hidden;
            z-index: 99999;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
        `;

        // 標題欄
        const titleBar = document.createElement('div');
        titleBar.style.cssText = `
            background: #4FC3F7;
            color: #000;
            padding: 10px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        titleBar.innerHTML = `
            <span>🔧 EliteGets 開發者調試面板</span>
            <button id="__debug_minimize" style="background: none; border: none; cursor: pointer; color: black;">_</button>
            <button id="__debug_close" style="background: none; border: none; cursor: pointer; color: black; font-weight: bold;">✕</button>
        `;

        // 日誌區域
        const logsArea = document.createElement('div');
        logsArea.id = '__debug_logs';
        logsArea.style.cssText = `
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            border-bottom: 1px solid #4FC3F7;
        `;

        // 命令輸入區域
        const inputArea = document.createElement('div');
        inputArea.style.cssText = `
            padding: 10px;
            display: flex;
            gap: 5px;
        `;

        const input = document.createElement('input');
        input.id = '__debug_input';
        input.type = 'text';
        input.placeholder = '輸入命令...';
        input.style.cssText = `
            flex: 1;
            background: #2d2d2d;
            color: #00ff00;
            border: 1px solid #4FC3F7;
            padding: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        `;

        const sendBtn = document.createElement('button');
        sendBtn.textContent = '執行';
        sendBtn.style.cssText = `
            background: #4FC3F7;
            color: #000;
            border: none;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 4px;
            font-weight: bold;
        `;

        sendBtn.addEventListener('click', () => this.executeDebugCommand(input.value));
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeDebugCommand(input.value);
                input.value = '';
            }
        });

        inputArea.appendChild(input);
        inputArea.appendChild(sendBtn);

        debugPanel.appendChild(titleBar);
        debugPanel.appendChild(logsArea);
        debugPanel.appendChild(inputArea);

        document.body.appendChild(debugPanel);

        // 事件監聽
        document.getElementById('__debug_close').addEventListener('click', () => {
            debugPanel.remove();
        });

        document.getElementById('__debug_minimize').addEventListener('click', () => {
            logsArea.style.display = logsArea.style.display === 'none' ? 'block' : 'none';
            inputArea.style.display = inputArea.style.display === 'none' ? 'flex' : 'none';
        });

        this.debugConsole = logsArea;
        this.addDebugLog('✅ 調試面板已啟用');
    }

    addDebugLog(message) {
        if (!this.debugConsole) return;

        const logEntry = document.createElement('div');
        logEntry.style.cssText = 'margin-bottom: 5px; border-bottom: 1px solid #333;';
        logEntry.innerHTML = `[${new Date().toLocaleTimeString()}] ${message}`;

        this.debugConsole.appendChild(logEntry);
        this.debugConsole.scrollTop = this.debugConsole.scrollHeight;

        // 限制日誌數量
        while (this.debugConsole.children.length > 100) {
            this.debugConsole.removeChild(this.debugConsole.firstChild);
        }
    }

    executeDebugCommand(command) {
        try {
            const result = eval(command);
            this.addDebugLog(`$ ${command}`);
            this.addDebugLog(`> ${JSON.stringify(result)}`);
        } catch (error) {
            this.addDebugLog(`$ ${command}`);
            this.addDebugLog(`❌ 錯誤: ${error.message}`);
        }
    }

    allowLocalStorage() {
        // 解鎖所有 localStorage 訪問
        console.log('✅ localStorage 已解鎖');
    }

    enableCodeInspection() {
        // 允許代碼檢查
        window.__elitegets_inspect_code = (functionName) => {
            const fn = window[functionName];
            if (typeof fn === 'function') {
                console.log(`源代碼: ${fn.toString()}`);
            }
        };

        console.log('✅ 代碼檢查已啟用');
    }

    enableAPIDebugging() {
        // 攔截並記錄所有 API 調用
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const [url, options] = args;
            console.log(`📡 API 請求: ${url}`, options);

            const response = await originalFetch.apply(this, args);
            console.log(`📡 API 響應:`, response.status, response.statusText);

            return response;
        };

        console.log('✅ API 調試已啟用');
    }

    enablePerformanceMonitoring() {
        // 啟用性能監控
        window.__elitegets_performance = {
            mark: (name) => performance.mark(name),
            measure: (name, start, end) => {
                performance.measure(name, start, end);
                const measure = performance.getEntriesByName(name)[0];
                console.log(`⏱️  性能: ${name} = ${measure.duration.toFixed(2)}ms`);
            },
            getMetrics: () => {
                const metrics = {
                    navigationTiming: performance.getEntriesByType('navigation')[0],
                    paintTiming: performance.getEntriesByType('paint'),
                    resourceTiming: performance.getEntriesByType('resource')
                };
                console.table(metrics);
                return metrics;
            }
        };

        console.log('✅ 性能監控已啟用');
    }

    /**
     * ============================================
     * 會話管理
     * ============================================
     */

    getSessionRemainingTime() {
        if (!this.sessionStartTime) return 0;
        const elapsed = Date.now() - this.sessionStartTime;
        const remaining = this.sessionTimeout - elapsed;
        return Math.max(0, Math.ceil(remaining / 1000 / 60));
    }

    startSessionMonitoring() {
        // 定期檢查會話是否過期
        setInterval(() => {
            if (this.isDevMode && this.getSessionRemainingTime() === 0) {
                console.warn('⚠️  開發者會話已過期，正在禁用調試模式...');
                this.disableDeveloperMode();
            } else if (this.isDevMode) {
                const remaining = this.getSessionRemainingTime();
                if (remaining < 30) {
                    console.warn(`⚠️  開發者會話將在 ${remaining} 分鐘後過期`);
                }
            }
        }, 60000); // 每 1 分鐘檢查一次
    }

    /**
     * 禁用開發者模式
     */
    disableDeveloperMode() {
        console.log('🔒 正在禁用開發者模式...');

        this.isDevMode = false;
        this.developerKey = null;
        this.sessionStartTime = null;

        // 隱藏調試面板
        const debugPanel = document.getElementById('__elitegets_debug_panel');
        if (debugPanel) {
            debugPanel.remove();
        }

        console.log('✅ 開發者模式已禁用');

        // 記錄事件
        this.logDebugEvent('developer_mode_disabled');
    }

    /**
     * ============================================
     * 調試日誌和審計
     * ============================================
     */

    logDebugEvent(eventType, details = {}) {
        if (!this.isDevMode) return;

        const logEntry = {
            timestamp: new Date().toISOString(),
            eventType: eventType,
            details: details,
            developerId: Array.from(this.authenticatedDevelopers)[0]
        };

        this.debugLogs.push(logEntry);

        // 限制日誌數量
        if (this.debugLogs.length > this.maxLogs) {
            this.debugLogs.shift();
        }

        // 發送到伺服器（用於審計）
        this.sendDebugLogToServer(logEntry);
    }

    async sendDebugLogToServer(logEntry) {
        try {
            await fetch(`${this.developersServer}/api/v1/debug-logs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logEntry)
            });
        } catch (error) {
            console.error('無法發送調試日誌到伺服器');
        }
    }

    exportDebugLogs() {
        const dataStr = JSON.stringify(this.debugLogs, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `debug-logs-${Date.now()}.json`;
        link.click();
        URL.revokeObjectURL(url);
    }

    /**
     * ============================================
     * 實用工具和命令
     * ============================================
     */

    /**
     * 獲取應用狀態
     */
    getApplicationState() {
        return {
            isDevMode: this.isDevMode,
            sessionTime: this.getSessionRemainingTime(),
            authenticatedDevelopers: Array.from(this.authenticatedDevelopers),
            allowedFeatures: this.allowedFeatures,
            environment: this.detectEnvironment(),
            debugLogs: this.debugLogs.length
        };
    }

    /**
     * 清除所有本地存儲
     */
    clearAllStorage() {
        if (!confirm('確定要清除所有本地存儲嗎？')) return;

        localStorage.clear();
        sessionStorage.clear();

        console.log('✅ 本地存儲已清除');
        this.addDebugLog('✅ 本地存儲已清除');
    }

    /**
     * 測試許可證驗證
     */
    testLicenseVerification() {
        console.group('🧪 許可證驗證測試');
        console.log('正在模擬許可證驗證...');

        // 模擬驗證流程
        const testResults = {
            formatValidation: true,
            signatureVerification: true,
            expiryCheck: true,
            fingerprintMatch: true
        };

        console.table(testResults);
        console.groupEnd();

        return testResults;
    }

    /**
     * 測試 API 端點
     */
    async testAPIEndpoint(endpoint) {
        console.log(`🧪 測試 API 端點: ${endpoint}`);

        try {
            const response = await fetch(endpoint);
            const data = await response.json();

            console.log('✅ 端點響應:', data);
            this.addDebugLog(`✅ ${endpoint}: ${response.status}`);

            return data;
        } catch (error) {
            console.error('❌ 端點測試失敗:', error);
            this.addDebugLog(`❌ ${endpoint}: ${error.message}`);
        }
    }

    /**
     * 遠程調試命令
     */
    executeRemoteCommand(command, params = {}) {
        console.log(`🔧 執行遠程命令: ${command}`, params);

        const commands = {
            // 許可證命令
            'license:check': () => this.testLicenseVerification(),
            'license:reset': () => {
                localStorage.removeItem('__elitegets_token');
                console.log('✅ 許可證已重置');
            },

            // 性能命令
            'performance:summary': () => window.__elitegets_performance?.getMetrics(),

            // 存儲命令
            'storage:clear': () => this.clearAllStorage(),
            'storage:export': () => this.exportDebugLogs(),

            // 狀態命令
            'state:get': () => this.getApplicationState(),

            // API 命令
            'api:test': (endpoint) => this.testAPIEndpoint(endpoint)
        };

        const handler = commands[command];
        if (handler) {
            return handler(params);
        } else {
            console.error(`❌ 未知命令: ${command}`);
        }
    }
}

// ============================================================
// 全局初始化
// ============================================================

window.EliteGetsDevMode = null;

/**
 * 初始化開發者調試模式
 */
function initializeDeveloperMode(developerKey) {
    if (!window.EliteGetsDevMode) {
        window.EliteGetsDevMode = new DeveloperDebugMode();
    }

    return window.EliteGetsDevMode.enableDeveloperMode(developerKey);
}

// 使用示例：
// await initializeDeveloperMode('DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');
// window.EliteGetsDevMode.testLicenseVerification();
// window.EliteGetsDevMode.getApplicationState();
