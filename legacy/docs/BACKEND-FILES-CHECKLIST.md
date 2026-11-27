# 📋 後端完整文件清單

## 🎯 後端部署文件（8 個）

### ✅ 核心 API 服務

#### 1. FastAPI 許可證驗證服務
**文件**: `backend-license-verification.py`
**技術棧**: Python 3.9+, FastAPI, PostgreSQL, Redis
**主要端點**:

```
POST /api/v2/verify              - 驗證許可證
POST /api/v2/revoke              - 吊銷許可證
POST /api/v2/report-event        - 報告安全事件
GET  /api/v2/revocation-list     - 吊銷清單
GET  /api/v2/audit-logs          - 審計日誌
GET  /health                     - 健康檢查
GET  /docs                       - Swagger 文檔
```

**依賴**:
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.0
pydantic==2.4.2
cryptography==41.0.7
jwt==1.3.0
```

---

#### 2. Node.js Express 後端（可選）
**文件**: `backend-nodejs-api.ts`
**技術棧**: Node.js 18+, Express, TypeScript, PostgreSQL
**用途**: 替代方案或補充服務

**依賴**:
```json
{
  "express": "^4.18.2",
  "pg": "^8.11.3",
  "redis": "^4.6.10",
  "jsonwebtoken": "^9.1.2",
  "bcryptjs": "^2.4.3"
}
```

---

### ✅ 機器學習和預測

#### 3. LSTM 預測服務
**文件**: `lstm-prediction-service.py`
**用途**: 用電量預測、異常檢測、趨勢分析
**輸入**: 歷史用電數據
**輸出**: 預測值 + 置信度

**依賴**:
```
tensorflow==2.14.0
keras==2.14.0
numpy==1.24.3
pandas==2.1.1
scikit-learn==1.3.2
```

---

### ✅ 企業集成

#### 4. 企業集成模塊
**文件**: `enterprise-integration.py`
**集成列表**:

- **SAP**: ERP 數據對接
- **釘釘**: 企業通訊和審批
- **微信**: 消息推送和企業應用
- **Slack**: 團隊通知
- **MS Teams**: 團隊協作

**依賴**:
```
requests==2.31.0
dingtalk-sdk==1.3.7
wechat-sdk==1.8.0
slack-sdk==3.26.0
```

---

### ✅ 通訊協議

#### 5. MQTT 橋接
**文件**: `mqtt-bridge.js`
**用途**: MQTT 設備連接、消息轉換
**功能**: MQTT → HTTP API 轉換

**依賴**:
```json
{
  "mqtt": "^5.0.2",
  "node-red": "^3.1.0"
}
```

---

### ✅ 配置和初始化

#### 6. Docker Compose
**文件**: `docker-compose.yml`
**包含服務**:

```yaml
services:
  frontend:        # Nginx Web 伺服器
  backend:         # FastAPI 主服務
  database:        # PostgreSQL 數據庫
  redis:           # 快取和會話存儲
  influxdb:        # 時間序列數據庫
  mosquitto:       # MQTT Broker
  prometheus:      # 監控數據
  grafana:         # 可視化儀表板
```

---

#### 7. 環境配置文件
**文件**: `.env.backend`

```env
# 數據庫
DATABASE_URL=postgresql://user:password@db:5432/elitegets
DB_USER=elitegets
DB_PASSWORD=secure_password_here
DB_NAME=elitegets

# Redis
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=redis_password_here

# JWT
JWT_SECRET=your_super_secure_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION=86400

# MQTT
MQTT_BROKER=mqtt://mosquitto:1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password

# 許可證伺服器
LICENSE_SERVER_URL=https://license.elitegets.com
DEVELOPER_PORTAL_URL=https://developers.elitegets.com

# API 設置
API_VERSION=v2
API_PORT=8000
API_HOST=0.0.0.0

# 日誌
LOG_LEVEL=INFO
LOG_FILE=/var/log/elitegets/backend.log

# 郵件
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 安全設置
CORS_ORIGINS=["http://localhost:3001", "https://yourdomain.com"]
ALLOWED_HOSTS=["localhost", "yourdomain.com"]
```

---

#### 8. 數據庫初始化
**文件**: `alembic/versions/001_initial.py`

```python
# 創建表
- users
- licenses
- devices
- audit_logs
- api_keys
- revocation_list
- meter_data
- predictions
```

---

## 📊 後端總大小和資源

| 組件 | 大小 | 內存 | CPU | 磁盤 |
|------|------|------|-----|------|
| FastAPI | 150KB | 100MB | 5% | - |
| PostgreSQL | - | 200MB | 10% | 5GB |
| Redis | - | 50MB | 2% | 1GB |
| InfluxDB | - | 100MB | 5% | 10GB |
| Mosquitto | - | 20MB | 1% | 100MB |
| **總計** | - | ~470MB | ~23% | 16GB+ |

---

## 🚀 後端部署步驟

### 方式 1：Docker Compose（推薦）

```bash
# 1. 準備目錄
mkdir -p /opt/elitegets/{backend,data,logs}
cd /opt/elitegets

# 2. 複製檔案
cp docker-compose.yml .
cp .env.backend .
cp -r backend/* ./backend/

# 3. 構建和啟動
docker-compose up -d

# 4. 驗證
docker-compose ps
docker-compose logs backend

# 5. 初始化數據庫
docker-compose exec backend alembic upgrade head

# 6. 創建超級用戶
docker-compose exec backend python -c "
from app.db import create_admin_user
create_admin_user('admin@elitegets.com', 'AdminPassword123')
"
```

---

### 方式 2：手動部署

```bash
# 1. 系統要求
- Python 3.9+
- PostgreSQL 12+
- Redis 6.0+
- Linux/macOS

# 2. 虛擬環境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 環境配置
cp .env.backend.example .env.backend
# 編輯 .env.backend 設置數據庫信息

# 5. 數據庫遷移
alembic upgrade head

# 6. 啟動服務
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 7. 訪問
http://localhost:8000/docs
```

---

## 🔐 API 安全配置

```python
# JWT 配置
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

# API 速率限制
RATE_LIMIT_REQUESTS = 1000
RATE_LIMIT_WINDOW = 3600  # 1 小時

# CORS 配置
CORS_ORIGINS = [
    "http://localhost:3001",
    "http://localhost:3000",
    "https://yourdomain.com"
]

# 密鑰管理
RSA_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
...(RSA-4096 私鑰)...
-----END PRIVATE KEY-----"""

RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
...(RSA-4096 公鑰)...
-----END PUBLIC KEY-----"""
```

---

## 📡 API 端點文檔

### 許可證驗證

```http
POST /api/v2/verify
Content-Type: application/json

{
  "licenseKey": "encrypted_key",
  "deviceFingerprint": "sha256_hash",
  "timestamp": 1699000000,
  "signature": "hmac_signature"
}

Response 200:
{
  "valid": true,
  "mode": "online",
  "features": {...},
  "expiryDate": "2025-01-01",
  "token": "offline_token_jwt"
}
```

---

### 事件報告

```http
POST /api/v2/report-event
Authorization: Bearer <token>
Content-Type: application/json

{
  "eventType": "tampering_detected",
  "deviceFingerprint": "hash",
  "details": {
    "reason": "code_modification",
    "timestamp": 1699000000
  }
}

Response 200:
{
  "reported": true,
  "eventId": "evt_xxxxx"
}
```

---

### 審計日誌

```http
GET /api/v2/audit-logs?limit=100&offset=0
Authorization: Bearer <admin_token>

Response 200:
{
  "logs": [
    {
      "id": "log_xxxxx",
      "timestamp": "2024-01-15T10:30:00Z",
      "eventType": "license_verified",
      "developerId": "dev_001",
      "details": {...}
    }
  ],
  "total": 1500
}
```

---

## 🧪 後端測試檢查清單

```
☑️ 健康檢查
   curl http://localhost:8000/health

☑️ API 文檔可訪問
   http://localhost:8000/docs

☑️ 數據庫連接正常
   docker-compose exec backend psql -U user -d elitegets -c "\dt"

☑️ Redis 正常工作
   docker-compose exec redis redis-cli ping
   # 應返回 PONG

☑️ 許可證驗證端點
   curl -X POST http://localhost:8000/api/v2/verify \
     -H "Content-Type: application/json" \
     -d '{...}'

☑️ 事件報告端點
   curl -X POST http://localhost:8000/api/v2/report-event \
     -H "Content-Type: application/json" \
     -d '{...}'

☑️ 審計日誌可訪問
   curl http://localhost:8000/api/v2/audit-logs \
     -H "Authorization: Bearer <token>"

☑️ MQTT 橋接工作
   mosquitto_sub -h localhost -t "test/topic"
   mosquitto_pub -h localhost -t "test/topic" -m "test"

☑️ 性能基線
   - 平均響應時間 < 200ms
   - P95 < 500ms
   - 錯誤率 < 0.1%

☑️ 所有容器運行中
   docker-compose ps
```

---

## 🔄 數據庫架構

```sql
-- 用戶表
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255),
  role VARCHAR(50),
  created_at TIMESTAMP
);

-- 許可證表
CREATE TABLE licenses (
  id UUID PRIMARY KEY,
  license_key VARCHAR(255) UNIQUE,
  user_id UUID REFERENCES users(id),
  version VARCHAR(50),
  status VARCHAR(50),
  expiry_date TIMESTAMP
);

-- 設備表
CREATE TABLE devices (
  id UUID PRIMARY KEY,
  device_fingerprint VARCHAR(255),
  license_id UUID REFERENCES licenses(id),
  last_verified TIMESTAMP
);

-- 審計日誌表
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  event_type VARCHAR(255),
  developer_id VARCHAR(255),
  details JSONB,
  created_at TIMESTAMP
);

-- 吊銷清單表
CREATE TABLE revocation_list (
  id UUID PRIMARY KEY,
  license_id UUID,
  revoked_at TIMESTAMP,
  reason VARCHAR(255)
);
```

---

## 📊 監控和日誌

### Prometheus 指標

```
- http_requests_total
- http_request_duration_seconds
- database_connections_active
- license_verification_success_rate
- api_errors_total
```

### 日誌文件位置

```
/var/log/elitegets/backend.log     - 應用日誌
/var/log/elitegets/access.log      - 訪問日誌
/var/log/elitegets/error.log       - 錯誤日誌
/var/log/elitegets/audit.log       - 審計日誌
```

---

## 🚨 故障排查

### 問題 1：數據庫連接超時

```bash
# 檢查 PostgreSQL 容器
docker-compose logs postgres

# 檢查連接信息
docker-compose exec backend python -c "
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL'))
print(engine.execute('SELECT 1'))
"
```

### 問題 2：許可證驗證失敗

```bash
# 檢查日誌
docker-compose logs backend | grep verify

# 檢查密鑰格式
# 應為: DEV-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# 測試端點
curl -X POST http://localhost:8000/api/v2/verify \
  -H "Content-Type: application/json" \
  -d '{"licenseKey":"test","deviceFingerprint":"test"}'
```

---

## ✅ 部署檢查清單

```
部署前:
☑️ 所有後端文件已準備
☑️ 數據庫密碼已設置
☑️ JWT 密鑰已生成
☑️ 環境變量已配置

部署中:
☑️ Docker Compose 啟動成功
☑️ 所有容器運行中
☑️ 數據庫已初始化
☑️ 遷移已完成

部署後:
☑️ API 端點可用
☑️ 數據庫可連接
☑️ Redis 正常工作
☑️ MQTT 正常連接
☑️ 日誌記錄正常
☑️ 監控告警配置
☑️ 備份已設置
```

---

**所有後端文件已準備就緒！** 🚀
