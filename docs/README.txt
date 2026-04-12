╔════════════════════════════════════════════════════════════╗
║    EliteGets 企業級能源管理平台 - Windows 部署包            ║
╚════════════════════════════════════════════════════════════╝

📋 包內容：
✅ docker-compose.yml        - Docker 編排配置
✅ .env.example             - 環境變量模板
✅ 所有 HTML 頁面           - 前端應用
✅ 所有 JavaScript 文件     - 前端邏輯
✅ 所有後端 Python 文件     - 後端服務
✅ 完整文檔指南             - 部署說明

🚀 快速開始（5 步，15 分鐘）：

第 1 步：解壓此包到 C:\elitegets\

第 2 步：閱讀部署指南
  • 先讀 STEP-BY-STEP.txt
  • 或讀 WINDOWS-DEPLOYMENT-GUIDE.md

第 3 步：安裝 Docker Desktop
  下載: https://www.docker.com/products/docker-desktop

第 4 步：編輯 .env 文件
  在 C:\elitegets\ 中編輯 .env.example
  改名為 .env
  設置 DB_PASSWORD 和 JWT_SECRET

第 5 步：啟動部署
  打開 PowerShell
  進入: cd C:\elitegets
  執行: docker-compose up -d
  訪問: http://localhost/

📖 重要文檔：
  ⭐ STEP-BY-STEP.txt           - 必讀！5 步快速指南
  ⭐ WINDOWS-DEPLOYMENT-GUIDE.md - Windows 完整指南
  ⭐ QUICK-START-DEPLOYMENT.md   - 詳細部署流程

🎯 所需工具：
  ✅ Windows 10/11
  ✅ Docker Desktop（包含 Docker Compose）
  ✅ 4GB RAM
  ✅ 20GB 磁盤空間

📞 遇到問題？
  1. 查看 STEP-BY-STEP.txt 的故障排查部分
  2. 檢查 docker-compose logs
  3. 驗證 .env 文件配置

祝您部署順利！🚀
