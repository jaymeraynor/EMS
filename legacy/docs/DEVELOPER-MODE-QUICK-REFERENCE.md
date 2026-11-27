# 🔧 開發者調試模式 - 快速參考

## 🚀 30秒快速開始

```javascript
// 1. 在控制台中複製您的密鑰並粘貼：
await initializeDeveloperMode('DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');

// 2. 看到這個：
// ✅ 開發者模式已啟用
// 👨‍💻 開發者: Your Name
// ⏰ 會話時限: 480分鐘

// 3. 完成！調試面板已出現 🎉
```

---

## 📋 常用命令

```javascript
// 獲取應用狀態
window.EliteGetsDevMode.getApplicationState();

// 測試許可證
window.EliteGetsDevMode.testLicenseVerification();

// 測試 API
await window.EliteGetsDevMode.testAPIEndpoint('/api/v2/verify');

// 清除存儲
window.EliteGetsDevMode.clearAllStorage();

// 導出日誌
window.EliteGetsDevMode.exportDebugLogs();

// 檢查剩餘時間
window.EliteGetsDevMode.getSessionRemainingTime();
```

---

## 🎮 調試面板

- **位置**: 右下角固定面板
- **實時日誌**: 所有事件和命令輸出
- **命令執行**: 輸入 JS 並按 Enter 執行
- **最小化**: 點擊 `_` 按鈕
- **關閉**: 點擊 `✕` 按鈕

---

## ⏰ 重要限制

| 項目 | 限制 |
|------|------|
| 會話時間 | 8 小時 |
| 檢查間隔 | 每 1 分鐘 |
| 過期警告 | 30 分鐘前 |
| 自動禁用 | 會話過期時 |

---

## 🔑 密鑰申請

1. 📧 發送郵件到: `developers@elitegets.com`
2. ✍️ 提供: 名字、職位、項目名稱
3. ✅ 簽署 NDA
4. 🎫 獲得密鑰: `DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

---

## ⚠️ 安全提醒

```
✅ 只在開發環境中使用
✅ 不要分享密鑰
✅ 定期檢查審計日誌
✅ 會話過期時申請新密鑰

❌ 不要在生產環境中啟用
❌ 不要修改日誌
❌ 不要分享密鑰給他人
❌ 不要繞過安全檢查
```

---

## 🆘 常見問題

**Q: 密鑰驗證失敗？**
A: 檢查格式、過期日期、設備 MAC 地址

**Q: 會話過期了？**
A: 會話限制 8 小時，申請新密鑰

**Q: 調試面板不顯示？**
A: 清除緩存、刷新頁面、檢查控制台

**Q: 能在生產環境中使用嗎？**
A: 不能！僅限開發環境

---

## 📞 支持

- 📧 Email: `developers@elitegets.com`
- 💬 Slack: `#elitegets-developers`
- 🔗 Wiki: `https://developers.elitegets.com`

---

## 🎯 典型工作流

```
1️⃣ 申請開發者密鑰（收到郵件中的密鑰）
   ↓
2️⃣ 在控制台啟用開發者模式（複製密鑰並執行）
   ↓
3️⃣ 調試面板出現（在右下角）
   ↓
4️⃣ 使用調試命令進行測試
   ↓
5️⃣ 導出日誌供後續分析
   ↓
6️⃣ 會話過期時申請新密鑰
```

---

**記住：開發者模式 = 完全調試訪問 = 強大的工具 = 巨大的責任！** 🚀

安全使用，快樂調試！
