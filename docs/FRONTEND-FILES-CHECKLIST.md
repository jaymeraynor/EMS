# 📋 前端完整文件清單

## 🎯 前端部署文件（15 個）

### ✅ 核心保護系統（3 個）

| 文件名 | 大小 | 用途 | 依賴 |
|-------|------|------|------|
| `universal-protection-system.js` | 50KB | 所有版本防護系統 | 無 |
| `developer-debug-mode.js` | 40KB | 開發者調試模式 | 無 |
| `meter-adapter-engine.js` | 80KB | 電表適配器（15+協議） | 無 |

---

### ✅ 版本管理文件（4 個）

| 文件名 | 大小 | 功能 | 離線支持 |
|-------|------|------|---------|
| `meter-management-system-advance.html` | 100KB | Advance（Free） | 7 天 |
| `meter-management-system-pro.html` | 150KB | Pro（$490/年） | 14 天 |
| `meter-management-system-ultimate.html` | 200KB | Ultimate（$1490/年） | 30 天 |
| `meter-system-version-selector.html` | 80KB | 版本選擇和對比 | - |

---

### ✅ 功能模塊（5 個）

| 文件名 | 大小 | 功能 |
|-------|------|------|
| `electricity-bill-carbon-calculator.html` | 70KB | 電費計算 + 碳當量 |
| `ai-electricity-analyzer.html` | 90KB | AI 智能分析 |
| `renewable-energy-detailed-system.html` | 110KB | 可再生能源管理 |
| `building-configuration-system.html` | 95KB | 建築拖放配置 |
| `charging-station-pure.html` | 120KB | 充電樁管理（Ultimate專屬） |

---

### ✅ 儀表板（3 個）

| 文件名 | 大小 | 用途 |
|-------|------|------|
| `main-dashboard-mobile.html` | 150KB | 前台實時監控（RWD） |
| `admin-dashboard-pure.html` | 180KB | 後台管理系統 |
| `all-versions-protected-template.html` | 60KB | 通用模板（可選） |

---

## 📊 前端總大小

- **JavaScript**: 170KB
- **HTML 文件**: 1,390KB
- **總計**: ~1.5MB

---

## 🚀 前端部署步驟

### 方式 1：直接部署（簡單）

```bash
# 1. 創建前端目錄
mkdir -p /var/www/elitegets
cd /var/www/elitegets

# 2. 複製所有文件
cp /source/path/*.html ./
cp /source/path/*.js ./

# 3. 安裝簡單 HTTP 伺服器
npm install -g http-server

# 4. 啟動伺服器
http-server -p 3001 -c-1

# 5. 訪問
http://localhost:3001/meter-system-version-selector.html
```

---

### 方式 2：Nginx 部署（推薦）

```bash
# 1. 複製文件
cp /source/path/*.html /var/www/elitegets/
cp /source/path/*.js /var/www/elitegets/

# 2. Nginx 配置
cat > /etc/nginx/sites-available/elitegets << EOF
server {
    listen 80;
    server_name localhost;
    root /var/www/elitegets;
    index meter-system-version-selector.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 禁用緩存（開發環境）
    location ~* \.(html|js)$ {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
EOF

# 3. 啟用站點
ln -s /etc/nginx/sites-available/elitegets /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 4. 訪問
http://localhost/meter-system-version-selector.html
```

---

### 方式 3：Docker 部署

```bash
# Dockerfile
cat > Dockerfile << EOF
FROM nginx:alpine
COPY ./*.html /usr/share/nginx/html/
COPY ./*.js /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

# 構建和運行
docker build -t elitegets-frontend .
docker run -p 3001:80 elitegets-frontend
```

---

## 🧪 前端測試檢查清單

```
☑️ 訪問版本選擇器頁面
   http://localhost:3001/meter-system-version-selector.html

☑️ 測試三個版本頁面
   - Advance: http://localhost:3001/meter-management-system-advance.html
   - Pro: http://localhost:3001/meter-management-system-pro.html
   - Ultimate: http://localhost:3001/meter-management-system-ultimate.html

☑️ 驗證防護系統
   - 控制台應顯示許可證驗證日誌
   - F12 應被阻止
   - 右鍵菜單應被禁用
   - 複製功能應被禁用

☑️ 測試所有功能模塊
   - 電費計算器
   - AI 分析系統
   - 可再生能源管理
   - 建築配置系統
   - 充電樁管理

☑️ 測試儀表板
   - 前台儀表板
   - 後台管理系統

☑️ 性能檢查
   - 頁面加載時間 < 2 秒
   - 所有資源加載成功
   - 控制台無錯誤
```

---

## 🔑 許可證配置

```javascript
// 設置許可證密鑰（在 HTML 中）
<script>
    window.ELITEGETS_LICENSE_KEY = 'your_license_key_here';
</script>

// 或在 localStorage 中
localStorage.setItem('__elitegets_license_key', 'your_license_key_here');

// 或在 HTML 屬性中
<html data-license-key="your_license_key_here">
```

---

## 🔧 環境變量（前端）

```bash
# .env.frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_LICENSE_SERVER=http://localhost:8000
REACT_APP_ENVIRONMENT=development
REACT_APP_VERSION=1.0.0
REACT_APP_DEBUG_MODE=false
```

---

## 📝 常見問題

### Q1: 許可證驗證失敗
**A**: 檢查許可證密鑰格式和有效期

### Q2: 頁面加載很慢
**A**: 禁用緩存，檢查網絡連接

### Q3: 開發者工具未被阻止
**A**: 確認 `universal-protection-system.js` 已加載

### Q4: 能否禁用防護進行開發
**A**: 使用開發者密鑰啟用調試模式

---

**所有前端文件已準備就緒，準備好部署了嗎？** 🚀
