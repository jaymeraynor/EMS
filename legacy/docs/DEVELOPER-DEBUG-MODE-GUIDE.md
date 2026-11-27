# 🔧 EliteGets 開發者調試模式使用指南

## 📋 概述

**開發者調試模式** 是一個安全且受控的調試環境，允許授權的開發人員在受保護的應用中進行調試工作，同時保持生產環境的安全性。

---

## 🔑 獲取開發者密鑰

### 申請流程

```
1. 聯繫: developers@elitegets.com
2. 提供: 
   ├─ 姓名和職位
   ├─ 員工/承包商 ID
   ├─ 項目名稱
   ├─ 預期使用期限
   └─ 機器 MAC 地址

3. 驗證: 身份和權限檢查
4. 簽署: NDA 和安全協議
5. 頒發: DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 密鑰格式

```
格式: DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
長度: 40 個字符
有效期: 3 個月
綁定設備: 一個機器 ID
```

### 密鑰示例

```
✅ 有效格式:
DEV-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456

❌ 無效格式:
dev-xxxx (小寫)
DEV-xxx (太短)
DEVELOP-xxxx (錯誤前綴)
```

---

## 🚀 啟用開發者模式

### 方法 1：直接在控制台中

```javascript
// 複製您的開發者密鑰
const devKey = 'DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX';

// 啟用開發者模式
await initializeDeveloperMode(devKey);

// 應該看到:
// ✅ 開發者模式已啟用
// 👨‍💻 開發者: Your Name
// ⏰ 會話時限: 480分鐘
```

### 方法 2：在 HTML 中設置

```html
<!-- 在頁面加載前添加 -->
<script>
    window.DEVELOPER_KEY = 'DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX';
</script>

<script src="/developer-debug-mode.js"></script>

<script>
    // 自動初始化
    if (window.DEVELOPER_KEY) {
        initializeDeveloperMode(window.DEVELOPER_KEY);
    }
</script>
```

### 方法 3：使用環境變量

```javascript
// 在開發伺服器中設置環境變量
process.env.ELITEGETS_DEV_KEY = 'DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX';

// 然後在應用中
const devKey = process.env.ELITEGETS_DEV_KEY;
if (devKey) {
    await initializeDeveloperMode(devKey);
}
```

---

## 🎮 調試面板

### 啟用後會顯示

```
┌─────────────────────────────────────────────┐
│ 🔧 EliteGets 開發者調試面板        _ ✕ │
├─────────────────────────────────────────────┤
│ [00:15:42] ✅ 調試面板已啟用                │
│ [00:15:43] ✅ 開發者工具已解鎖            │
│ [00:15:44] ✅ API 調試已啟用               │
│ [00:15:45] ✅ 性能監控已啟用               │
│                                             │
│ [輸入命令...                            [執行]│
└─────────────────────────────────────────────┘
```

### 面板功能

- **日誌區域**: 實時顯示所有調試事件和日誌
- **命令輸入**: 執行 JavaScript 命令
- **實時更新**: 每條命令結果立即顯示
- **最小化**: 點擊 `_` 按鈕以最小化面板

---

## 💻 調試命令

### 應用狀態命令

```javascript
// 獲取應用當前狀態
window.EliteGetsDevMode.getApplicationState();

// 返回:
{
    isDevMode: true,
    sessionTime: 480,
    authenticatedDevelopers: ["dev001"],
    allowedFeatures: ["debugging", "code-inspection", "api-testing"],
    environment: {
        isDevelopment: true,
        isLocalhost: true,
        isProduction: false,
        ...
    },
    debugLogs: 42
}
```

### 許可證測試命令

```javascript
// 測試許可證驗證流程
window.EliteGetsDevMode.testLicenseVerification();

// 測試單個端點
await window.EliteGetsDevMode.testAPIEndpoint('/api/v2/verify');

// 重置許可證
window.EliteGetsDevMode.executeRemoteCommand('license:reset');
```

### 性能監控命令

```javascript
// 標記開始
window.__elitegets_performance.mark('operation-start');

// 執行操作
// ...

// 標記結束並測量
window.__elitegets_performance.mark('operation-end');
window.__elitegets_performance.measure('operation', 'operation-start', 'operation-end');

// 獲取所有性能指標
window.__elitegets_performance.getMetrics();
```

### 存儲管理命令

```javascript
// 清除所有本地存儲
window.EliteGetsDevMode.clearAllStorage();

// 導出調試日誌（下載 JSON 文件）
window.EliteGetsDevMode.exportDebugLogs();

// 查看本地存儲
console.log(localStorage);
console.log(sessionStorage);
```

### 遠程命令執行

```javascript
// 執行預定義命令
window.EliteGetsDevMode.executeRemoteCommand('command-name', params);

// 可用命令:
'license:check'       // 檢查許可證狀態
'license:reset'       // 重置許可證
'performance:summary' // 獲取性能摘要
'storage:clear'       // 清除存儲
'storage:export'      // 導出日誌
'state:get'           // 獲取應用狀態
'api:test'            // 測試 API 端點
```

---

## 🧪 調試場景

### 場景 1：調試許可證驗證

```javascript
// 1. 啟用開發者模式
await initializeDeveloperMode('DEV-XXXXX');

// 2. 測試許可證驗證
window.EliteGetsDevMode.testLicenseVerification();

// 3. 檢查驗證日誌
console.log(window.EliteGetsDevMode.debugLogs);

// 4. 重置並重新測試
window.EliteGetsDevMode.executeRemoteCommand('license:reset');
// ... 重新加載應用
```

### 場景 2：調試 API 集成

```javascript
// 1. 啟用調試模式
await initializeDeveloperMode('DEV-XXXXX');

// 2. 測試 API 端點
await window.EliteGetsDevMode.testAPIEndpoint('/api/v2/meter/list');

// 3. 查看所有 API 調用（在控制台中自動記錄）
// 所有 fetch 調用都會被自動記錄

// 4. 檢查響應
window.EliteGetsDevMode.debugLogs.filter(log => log.eventType.includes('api'));
```

### 場景 3：性能分析

```javascript
// 1. 啟用開發者模式
await initializeDeveloperMode('DEV-XXXXX');

// 2. 測量加載時間
window.__elitegets_performance.mark('page-load-start');
// ... 加載頁面
window.__elitegets_performance.mark('page-load-end');
window.__elitegets_performance.measure('page-load', 'page-load-start', 'page-load-end');

// 3. 獲取性能指標
window.__elitegets_performance.getMetrics();
```

### 場景 4：代碼檢查

```javascript
// 1. 啟用開發者模式
await initializeDeveloperMode('DEV-XXXXX');

// 2. 檢查函數源代碼
window.__elitegets_inspect_code('verifyLicense');

// 3. 檢查應用狀態
window.EliteGetsDevMode.getApplicationState();

// 4. 查看所有調試日誌
window.EliteGetsDevMode.debugLogs;
```

---

## ⏰ 會話管理

### 會話信息

```
會話時限: 8 小時（480 分鐘）
自動檢查: 每 1 分鐘
過期警告: 剩餘 30 分鐘時顯示
自動禁用: 會話過期時
```

### 檢查剩餘時間

```javascript
// 獲取剩餘時間（分鐘）
const remaining = window.EliteGetsDevMode.getSessionRemainingTime();
console.log(`剩餘時間: ${remaining} 分鐘`);

// 獲取應用狀態（包含會話時間）
const state = window.EliteGetsDevMode.getApplicationState();
console.log(`剩餘會話: ${state.sessionTime} 分鐘`);
```

### 會話過期時

```
會話過期時，將自動：
1. 禁用開發者模式
2. 隱藏調試面板
3. 恢復保護機制
4. 記錄事件到審計日誌
```

---

## 🔒 安全特性

### 密鑰安全

```
✅ 密鑰格式驗證
✅ 伺服器端驗證
✅ 設備綁定（MAC 地址）
✅ 過期日期檢查
✅ 開發者狀態驗證
✅ 自動禁用已過期的密鑰
```

### 會話安全

```
✅ 自動會話超時（8 小時）
✅ 定期安全檢查
✅ 所有操作都被記錄
✅ 審計日誌發送到伺服器
✅ 異常行為檢測
```

### 日誌安全

```
✅ 調試日誌記錄
✅ 發送到伺服器審計
✅ 開發者身份標記
✅ 時間戳記錄
✅ 詳細事件跟蹤
```

---

## 📊 審計日誌

### 記錄的事件

```
開發者模式相關:
├─ developer_mode_enabled      (開發者模式啟用)
├─ developer_mode_disabled     (開發者模式禁用)
├─ invalid_key_format          (無效的密鑰格式)
├─ key_verification_failed     (密鑰驗證失敗)
├─ key_expired                 (密鑰已過期)
└─ developer_disabled          (開發者帳戶已禁用)

調試操作:
├─ console_debug               (控制台調試)
├─ api_request                 (API 請求)
├─ performance_check           (性能檢查)
├─ storage_access              (存儲訪問)
└─ code_inspection             (代碼檢查)
```

### 查看審計日誌

```javascript
// 查看本地調試日誌
window.EliteGetsDevMode.debugLogs;

// 按事件類型過濾
window.EliteGetsDevMode.debugLogs.filter(log => 
    log.eventType === 'api_request'
);

// 導出日誌供分析
window.EliteGetsDevMode.exportDebugLogs();
```

---

## ⚠️ 重要提醒

### ✅ 做這些事

```
✅ 定期更新開發者密鑰
✅ 會話過期後重新申請
✅ 在隔離的開發環境中調試
✅ 報告任何可疑活動
✅ 遵守 NDA 和安全協議
✅ 定期檢查審計日誌
```

### ❌ 不要做這些事

```
❌ 分享開發者密鑰
❌ 在生產環境中啟用開發者模式
❌ 修改密鑰或日誌
❌ 繞過安全檢查
❌ 訪問未授權的區域
❌ 上傳應用副本到未授權的位置
```

---

## 🆘 故障排除

### 問題 1：密鑰驗證失敗

```
症狀: "開發者密鑰驗證失敗"

解決方案:
1. 確認密鑰格式: DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
2. 檢查密鑰是否過期
3. 驗證設備 MAC 地址匹配
4. 檢查網絡連接
5. 聯繫 developers@elitegets.com
```

### 問題 2：會話自動過期

```
症狀: "開發者會話已過期"

解決方案:
1. 會話限制為 8 小時
2. 需要重新申請新密鑰
3. 或等待下一個 8 小時
4. 聯繫管理員延長會話
```

### 問題 3：調試面板不顯示

```
症狀: 調試面板沒有出現

解決方案:
1. 確保開發者模式已啟用
2. 檢查控制台是否有錯誤
3. 驗證腳本已正確加載
4. 清除瀏覽器緩存
5. 刷新頁面
```

### 問題 4：API 測試失敗

```
症狀: "端點測試失敗"

解決方案:
1. 檢查端點 URL 是否正確
2. 驗證網絡連接
3. 檢查 API 伺服器是否在線
4. 檢查許可證是否有效
5. 查看詳細錯誤信息
```

---

## 📞 支持聯繫

### 開發者支持

```
📧 Email: developers@elitegets.com
💬 Slack: #elitegets-developers
🔗 Wiki: https://developers.elitegets.com
🐛 Bug Report: https://bug-report.elitegets.com
```

### 工作時間

```
美國東部時間 (EST): 08:00 - 18:00 (週一至週五)
應應 (CET): 13:00 - 23:00 (週一至週五)
亞太地區 (SGT): 20:00 - 06:00 (下一天)(週一至週五)
```

---

## ✅ 檢查清單

### 開發者模式設置

```
☑️ 申請開發者密鑰
☑️ 簽署 NDA 和安全協議
☑️ 在開發環境中測試
☑️ 啟用開發者模式
☑️ 驗證所有功能解鎖
☑️ 開始調試工作
```

### 日常使用

```
☑️ 每天檢查會話時間
☑️ 定期檢查審計日誌
☑️ 不要在生產環境中使用
☑️ 會話過期前申請新密鑰
☑️ 報告任何異常行為
```

---

**祝您調試順利！** 🚀

如有任何問題，請聯繫開發者支持團隊。
