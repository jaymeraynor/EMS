# 🚀 EliteGets 快速部署指南（15 分鐘）

## 📋 前提條件

```bash
✓ Docker 已安裝（docker --version）
✓ Docker Compose 已安裝（docker-compose --version）
✓ 至少 2GB RAM 可用
✓ 至少 20GB 磁盤空間
✓ Linux/macOS 或 Windows (WSL2)
```

---

## 🎯 5 分鐘快速部署

### 步驟 1：準備文件（1 分鐘）

```bash
# 創建部署目錄
mkdir -p /opt/elitegets
cd /opt/elitegets

# 創建所需目錄結構
mkdir -p {frontend,backend,init-scripts,mosquitto,prometheus,grafana,loki,logs,nginx}

# 複製文件
# 前端文件
cp /source/*.html ./frontend/
cp /source/*.js ./frontend/

# 後端文件
cp /source/backend*.py ./backend/
cp /source/requirements.txt ./backend/
cp /source/Dockerfile ./backend/

# 配置文件
cp /source/docker-compose.yml ./
cp /source/.env.example ./.env
cp /source/*.yml ./prometheus/
cp /source/*.yml ./mosquitto/
cp /source/*.yml ./grafana/
```

---

### 步驟 2：配置環境（2 分鐘）

```bash
# 複製環境變量
cp .env.example .env

# 編輯 .env（設置密碼等）
nano .env

# 關鍵設置：
# - DB_PASSWORD: 生成安全密碼
# - JWT_SECRET: 生成 32+ 字符密鑰
# - REDIS_PASSWORD: 生成密碼
# - GRAFANA_PASSWORD: 設置密碼
```

---

### 步驟 3：啟動容器（1 分鐘）

```bash
# 構建鏡像
docker-compose build

# 啟動所有服務
docker-compose up -d

# 查看狀態
docker-compose ps
```

---

### 步驟 4：驗證部署（1 分鐘）

```bash
# 等待 30 秒讓容器完全啟動
sleep 30

# 檢查前端
curl http://localhost/
# 應返回 HTML

# 檢查後端
curl http://localhost:8000/health
# 應返回 {"status":"ok"}

# 檢查 API 文檔
# 訪問: http://localhost:8000/docs

# 檢查 Grafana
# 訪問: http://localhost:3000
# 用戶名: admin
# 密碼: <你設置的 GRAFANA_PASSWORD>
```

---

### 步驟 5：初始化數據庫（無需手動）

```bash
# Docker Compose 自動執行
# 但如需手動初始化：
docker-compose exec backend alembic upgrade head

# 創建超級用戶
docker-compose exec backend python -c "
from app.models import User
from app.db import SessionLocal, Base, engine

Base.metadata.create_all(bind=engine)
db = SessionLocal()
admin = User(email='admin@elitegets.com', password='admin123', role='admin')
db.add(admin)
db.commit()
print('✅ 超級用戶已創建')
"
```

---

## ✅ 部署驗證清單

```bash
# 1. 所有容器運行中
docker-compose ps

# 2. 前端可訪問
curl -I http://localhost/
# 應返回 200 OK

# 3. 後端 API 可用
curl http://localhost:8000/health
# 應返回 {"status":"ok"}

# 4. 數據庫已連接
docker-compose exec backend python -c "
from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv('DATABASE_URL'))
connection = engine.raw_connection()
print('✅ 數據庫已連接')
"

# 5. Redis 運行中
docker-compose exec redis redis-cli ping
# 應返回 PONG

# 6. MQTT 運行中
docker-compose exec mosquitto sh -c "mosquitto_pub -h localhost -t 'test' -m 'test'"
# 應返回成功

# 7. 監控系統就緒
curl http://localhost:9090/-/healthy
# 應返回 Prometheus

# 8. 可視化儀表板
# 訪問: http://localhost:3000
# Grafana 應顯示數據
```

---

## 📝 常見部署問題

### 問題 1：端口已被占用

```bash
# 找到占用的進程
lsof -i :80      # 前端
lsof -i :8000    # 後端
lsof -i :5432    # 數據庫
lsof -i :6379    # Redis

# 解決方案 1：停止占用的服務
kill -9 <PID>

# 解決方案 2：修改 docker-compose.yml 中的端口
# ports:
#   - "8080:80"  # 改為 8080
#   - "9000:8000" # 改為 9000
```

---

### 問題 2：容器啟動失敗

```bash
# 查看詳細錯誤日誌
docker-compose logs <service_name>

# 例如：
docker-compose logs backend
docker-compose logs database

# 常見原因：
# - 內存不足：需要至少 2GB RAM
# - 磁盤空間不足：需要至少 20GB
# - Docker daemon 未運行：systemctl start docker
```

---

### 問題 3：數據庫連接失敗

```bash
# 1. 檢查 PostgreSQL 狀態
docker-compose ps postgres

# 2. 檢查密碼設置
echo $DB_PASSWORD

# 3. 測試連接
docker-compose exec database psql -U elitegets -d elitegets -c "SELECT 1;"

# 4. 查看初始化日誌
docker-compose logs database
```

---

### 問題 4：API 返回 502 Bad Gateway

```bash
# 1. 檢查後端服務
docker-compose logs backend

# 2. 檢查後端健康狀態
curl http://localhost:8000/health

# 3. 重啟後端
docker-compose restart backend

# 4. 檢查 Nginx 配置
docker-compose logs frontend
```

---

## 🧪 功能測試

### 測試 1：許可證驗證

```bash
curl -X POST http://localhost:8000/api/v2/verify \
  -H "Content-Type: application/json" \
  -d '{
    "licenseKey": "test_license_key",
    "deviceFingerprint": "test_device_fingerprint"
  }'

# 應返回許可證驗證結果
```

---

### 測試 2：訪問前端頁面

```bash
# 版本選擇器
curl -I http://localhost/meter-system-version-selector.html
# 應返回 200

# Advance 版本
curl -I http://localhost/meter-management-system-advance.html
# 應返回 200

# Pro 版本
curl -I http://localhost/meter-management-system-pro.html
# 應返回 200

# Ultimate 版本
curl -I http://localhost/meter-management-system-ultimate.html
# 應返回 200
```

---

### 測試 3：查看日誌

```bash
# 後端日誌
docker-compose logs -f backend

# 前端日誌
docker-compose logs -f frontend

# 數據庫日誌
docker-compose logs -f database

# 所有日誌
docker-compose logs -f
```

---

## 📊 性能驗證

```bash
# 頁面加載時間測試
time curl -o /dev/null -s http://localhost/

# API 響應時間測試
time curl -o /dev/null -s http://localhost:8000/health

# 負載測試（可選，需要 Apache Bench）
ab -n 100 -c 10 http://localhost/

# 預期結果：
# - 頁面加載 < 500ms
# - API 響應 < 100ms
# - 無錯誤 (0 failed)
```

---

## 🔒 安全檢查

```bash
# 1. 檢查 HTTPS（生產環境）
# 配置 SSL 證書

# 2. 改變默認密碼
# PostgreSQL
docker-compose exec database psql -U elitegets -c "ALTER USER elitegets PASSWORD 'new_password';"

# Grafana
# 訪問 http://localhost:3000，登錄後改變密碼

# 3. 配置防火牆
ufw enable
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS

# 4. 驗證防護系統
# 打開前端頁面，控制台應顯示許可證驗證日誌
# 嘗試打開 DevTools（F12），應被阻止
```

---

## 📱 訪問應用

```
前端頁面:     http://localhost/
版本選擇器:   http://localhost/meter-system-version-selector.html
API 文檔:     http://localhost:8000/docs
Grafana:      http://localhost:3000 (admin/你的密碼)
Prometheus:   http://localhost:9090
```

---

## 🛑 停止和卸載

```bash
# 停止所有容器（保留數據）
docker-compose stop

# 啟動已停止的容器
docker-compose start

# 完全卸載（刪除容器和卷）
docker-compose down -v
```

---

## 📞 需要幫助？

```
部署問題: deployment@elitegets.com
技術支持: support@elitegets.com
緊急電話: +1-888-ELITEGETS
文檔: https://docs.elitegets.com
```

---

## ✅ 完成清單

```
☑️ Docker 和 Docker Compose 已安裝
☑️ 環境變量已配置
☑️ 容器已啟動
☑️ 所有服務運行中
☑️ 數據庫已初始化
☑️ 前端可訪問
☑️ 後端 API 可用
☑️ 監控系統就緒
☑️ 功能測試通過
☑️ 準備投入生產
```

---

**🎉 恭喜！您已成功部署 EliteGets！** 🚀

下一步：
1. 配置域名和 SSL
2. 設置備份策略
3. 配置監控告警
4. 啟用用戶管理
5. 開始使用系統
