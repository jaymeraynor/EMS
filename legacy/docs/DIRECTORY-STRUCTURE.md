# 📁 EliteGets 完整目錄結構和文件放置指南

## 🎯 根目錄結構

```
/opt/elitegets/                          ← 主部署目錄
├── .env                                  ← 環境變量配置（複製 .env.example）
├── .env.example                          ← 環境變量模板
├── docker-compose.yml                    ← Docker 編排配置
│
├── frontend/                             ← 前端應用目錄（Nginx 根目錄）
│   ├── *.html                           ← 所有 HTML 文件
│   └── *.js                             ← 所有 JavaScript 文件
│
├── backend/                              ← 後端應用目錄
│   ├── Dockerfile                        ← 容器構建文件
│   ├── requirements.txt                  ← Python 依賴
│   ├── main.py                          ← FastAPI 主應用
│   ├── models.py                        ← 數據模型
│   ├── routes.py                        ← API 路由
│   ├── database.py                      ← 數據庫配置
│   ├── auth.py                          ← 身份驗證
│   ├── alembic/                         ← 數據庫遷移
│   │   └── versions/                    ← 遷移文件
│   └── logs/                            ← 應用日誌
│
├── init-scripts/                         ← 初始化腳本
│   ├── 01-init.sql                      ← 數據庫初始化
│   └── 02-seed.sql                      ← 數據填充（可選）
│
├── nginx/                                ← Nginx 配置
│   ├── nginx.conf                       ← 主配置文件
│   ├── conf.d/                          ← 站點配置
│   │   └── default.conf                 ← 默認站點
│   └── ssl/                             ← SSL 證書
│       ├── cert.pem                     ← 證書文件
│       └── key.pem                      ← 私鑰文件
│
├── mosquitto/                            ← MQTT Broker 配置
│   ├── config/                          ← MQTT 配置
│   │   └── mosquitto.conf               ← 主配置文件
│   └── data/                            ← 數據持久化
│
├── prometheus/                           ← Prometheus 監控配置
│   ├── prometheus.yml                   ← Prometheus 配置
│   └── rules/                           ← 告警規則
│       └── alerts.yml                   ← 告警定義
│
├── grafana/                              ← Grafana 儀表板配置
│   ├── provisioning/                    ← 自動配置
│   │   ├── datasources/                 ← 數據源
│   │   │   └── prometheus.yml           ← Prometheus 數據源
│   │   └── dashboards/                  ← 儀表板定義
│   │       └── *.json                   ← 儀表板 JSON
│   └── data/                            ← Grafana 數據
│
├── loki/                                 ← Loki 日誌配置
│   └── loki-config.yml                  ← Loki 配置文件
│
├── logs/                                 ← 應用日誌目錄
│   ├── nginx/                           ← Nginx 日誌
│   ├── backend/                         ← 後端日誌
│   ├── postgres/                        ← 數據庫日誌
│   ├── redis/                           ← Redis 日誌
│   ├── mosquitto/                       ← MQTT 日誌
│   ├── prometheus/                      ← Prometheus 日誌
│   ├── grafana/                         ← Grafana 日誌
│   └── loki/                            ← Loki 日誌
│
├── data/                                 ← 數據持久化（Docker 卷）
│   ├── postgres/                        ← PostgreSQL 數據
│   ├── redis/                           ← Redis 數據
│   ├── influxdb/                        ← InfluxDB 數據
│   ├── mosquitto/                       ← MQTT 數據
│   ├── prometheus/                      ← Prometheus 數據
│   ├── grafana/                         ← Grafana 數據
│   └── loki/                            ← Loki 數據
│
└── docs/                                 ← 文檔目錄（可選）
    ├── QUICK-START-DEPLOYMENT.md        ← 快速開始
    ├── FRONTEND-FILES-CHECKLIST.md      ← 前端清單
    ├── BACKEND-FILES-CHECKLIST.md       ← 後端清單
    └── *.md                             ← 其他文檔
```

---

## 📂 詳細文件放置指南

### 1️⃣ 根目錄文件（直接放在 /opt/elitegets/）

```
/opt/elitegets/
├── .env                          ← 複製 .env.example 並編輯
├── .env.example                  ← 環境變量模板
├── docker-compose.yml            ← Docker 編排配置
├── QUICK-START-DEPLOYMENT.md     ← 部署指南（可選，留作參考）
└── FINAL-DEPLOYMENT-SUMMARY.md   ← 總結文檔（可選）
```

**複製命令：**
```bash
cp /source/path/.env.example /opt/elitegets/.env
cp /source/path/docker-compose.yml /opt/elitegets/
```

---

### 2️⃣ 前端文件 → frontend/ 目錄

```
/opt/elitegets/frontend/
│
├── HTML 文件（15 個）
├── meter-management-system-advance.html
├── meter-management-system-pro.html
├── meter-management-system-ultimate.html
├── meter-system-version-selector.html
├── electricity-bill-carbon-calculator.html
├── ai-electricity-analyzer.html
├── renewable-energy-detailed-system.html
├── building-configuration-system.html
├── charging-station-pure.html
├── main-dashboard-mobile.html
├── admin-dashboard-pure.html
├── all-versions-protected-template.html
├── demo-*.html                   ← 演示文件（可選）
│
├── JavaScript 文件（3 個核心）
├── universal-protection-system.js     ← 防盜版和防破解
├── developer-debug-mode.js            ← 開發者調試模式
├── meter-adapter-engine.js            ← 電表適配器
│
└── 其他 JS 文件（可選）
    ├── color-system.js
    ├── i18n-language-system.js
    ├── service-worker.js
    └── smart-meter-converter-toolkit.js
```

**複製命令：**
```bash
mkdir -p /opt/elitegets/frontend
cp /source/path/*.html /opt/elitegets/frontend/
cp /source/path/*.js /opt/elitegets/frontend/
```

---

### 3️⃣ 後端文件 → backend/ 目錄

```
/opt/elitegets/backend/
│
├── Dockerfile                    ← 容器構建文件
├── requirements.txt              ← Python 依賴
│
├── 主應用文件
├── main.py                      ← FastAPI 主應用
├── models.py                    ← 數據模型定義
├── routes.py                    ← API 路由
├── database.py                  ← 數據庫配置
├── auth.py                      ← 身份驗證邏輯
│
├── 服務文件
├── backend-python-fastapi.py    ← FastAPI 實現
├── backend-nodejs-api.ts        ← Node.js 實現（可選）
├── lstm-prediction-service.py   ← ML 預測服務
├── enterprise-integration.py    ← 企業集成
├── mqtt-bridge.js               ← MQTT 橋接
│
├── 許可證和保護
├── license-protection-system.js ← 許可證驗證
├── universal-license-protection.js ← 通用保護
│
├── alembic/                     ← 數據庫遷移工具
│   ├── alembic.ini             ← Alembic 配置
│   └── versions/                ← 遷移文件目錄
│       ├── 001_initial.py
│       └── 002_add_tables.py
│
├── logs/                        ← 應用日誌（運行時創建）
│   ├── app.log
│   ├── error.log
│   └── access.log
│
└── tests/                       ← 測試文件（可選）
    ├── test_api.py
    ├── test_auth.py
    └── test_database.py
```

**複製命令：**
```bash
mkdir -p /opt/elitegets/backend/alembic/versions
cp /source/path/Dockerfile /opt/elitegets/backend/
cp /source/path/requirements.txt /opt/elitegets/backend/
cp /source/path/*.py /opt/elitegets/backend/
cp /source/path/alembic/* /opt/elitegets/backend/alembic/
```

---

### 4️⃣ 初始化腳本 → init-scripts/ 目錄

```
/opt/elitegets/init-scripts/
├── 01-init.sql                  ← 數據庫初始化
│   ├── 創建表結構
│   ├── 創建索引
│   └── 設置權限
│
└── 02-seed.sql                  ← 初始數據（可選）
    ├── 測試用戶
    ├── 示例許可證
    └── 示例數據
```

**複製命令：**
```bash
mkdir -p /opt/elitegets/init-scripts
cp /source/path/*.sql /opt/elitegets/init-scripts/
```

---

### 5️⃣ Nginx 配置 → nginx/ 目錄

```
/opt/elitegets/nginx/
│
├── nginx.conf                   ← Nginx 主配置
│   ├── 工作進程配置
│   ├── 事件配置
│   └── HTTP 塊配置
│
├── conf.d/                      ← 站點配置
│   └── default.conf             ← 前端站點配置
│       ├── 監聽 80 端口
│       ├── 根目錄指向 /var/www/html
│       ├── 代理設置（API → 後端）
│       └── 緩存策略
│
└── ssl/                         ← SSL 證書（生產環境）
    ├── cert.pem                 ← 證書
    └── key.pem                  ← 私鑰
```

**複製命令：**
```bash
mkdir -p /opt/elitegets/nginx/conf.d /opt/elitegets/nginx/ssl
# 需要自行創建 nginx.conf 和 default.conf
```

**基本 nginx.conf：**
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    include /etc/nginx/conf.d/*.conf;
}
```

**基本 default.conf：**
```nginx
server {
    listen 80;
    server_name _;
    
    root /usr/share/nginx/html;
    index meter-system-version-selector.html;
    
    location / {
        try_files $uri $uri/ /meter-system-version-selector.html;
    }
    
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 6️⃣ MQTT 配置 → mosquitto/ 目錄

```
/opt/elitegets/mosquitto/
│
├── config/
│   └── mosquitto.conf           ← MQTT 配置
│       ├── listener 1883
│       ├── allow_anonymous false
│       └── password_file
│
└── data/                        ← MQTT 數據（運行時創建）
    └── mosquitto.db
```

**基本 mosquitto.conf：**
```
listener 1883
protocol mqtt

listener 9001
protocol websockets

allow_anonymous false
password_file /mosquitto/config/passwd

persistence true
persistence_location /mosquitto/data/
```

---

### 7️⃣ Prometheus 配置 → prometheus/ 目錄

```
/opt/elitegets/prometheus/
│
├── prometheus.yml               ← Prometheus 主配置
│   ├── 全局設置
│   ├── 告警規則
│   └── 抓取配置
│
└── rules/                       ← 告警規則
    └── alerts.yml               ← 告警定義
        ├── CPU 使用率告警
        ├── 內存告警
        └── API 性能告警
```

**基本 prometheus.yml：**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
```

---

### 8️⃣ Grafana 配置 → grafana/ 目錄

```
/opt/elitegets/grafana/
│
├── provisioning/                ← 自動配置
│   ├── datasources/             ← 數據源定義
│   │   └── prometheus.yml       ← Prometheus 數據源
│   │
│   └── dashboards/              ← 儀表板定義
│       ├── dashboard.yml        ← 儀表板配置
│       └── *.json               ← 儀表板 JSON 文件
│
└── data/                        ← Grafana 數據（運行時創建）
    └── grafana.db
```

---

### 9️⃣ Loki 配置 → loki/ 目錄

```
/opt/elitegets/loki/
└── loki-config.yml             ← Loki 日誌配置
    ├── auth_enabled: false
    ├── ingester 設置
    └── schema_config
```

---

### 🔟 日誌目錄 → logs/ 目錄

```
/opt/elitegets/logs/
├── nginx/                       ← Nginx 日誌
│   ├── access.log
│   └── error.log
│
├── backend/                     ← 後端應用日誌
│   ├── app.log
│   ├── error.log
│   └── audit.log
│
├── postgres/                    ← 數據庫日誌
├── redis/                       ← Redis 日誌
├── mosquitto/                   ← MQTT 日誌
├── prometheus/                  ← Prometheus 日誌
├── grafana/                     ← Grafana 日誌
└── loki/                        ← Loki 日誌
```

**注意：** 這些目錄和文件在容器運行時會自動創建。

---

### 1️⃣1️⃣ 數據目錄 → data/ 目錄

```
/opt/elitegets/data/
├── postgres/                    ← PostgreSQL 數據卷
│   └── pgdata/
│
├── redis/                       ← Redis 數據卷
├── influxdb/                    ← InfluxDB 數據卷
├── mosquitto/                   ← MQTT 數據卷
├── prometheus/                  ← Prometheus 數據卷
├── grafana/                     ← Grafana 數據卷
└── loki/                        ← Loki 數據卷
```

**注意：** Docker Compose 會自動管理這些卷。

---

## 🚀 快速設置指南

### 第 1 步：創建目錄結構

```bash
#!/bin/bash

# 創建主目錄
mkdir -p /opt/elitegets

# 創建子目錄
mkdir -p /opt/elitegets/{frontend,backend,init-scripts}
mkdir -p /opt/elitegets/{nginx/conf.d,nginx/ssl}
mkdir -p /opt/elitegets/{mosquitto/config,mosquitto/data}
mkdir -p /opt/elitegets/{prometheus,grafana/provisioning}
mkdir -p /opt/elitegets/{loki,logs}
mkdir -p /opt/elitegets/{data/{postgres,redis,influxdb,mosquitto,prometheus,grafana,loki}}

cd /opt/elitegets
```

### 第 2 步：複製文件

```bash
#!/bin/bash

SOURCE="/source/path"  # 改成實際源路徑

# 複製根目錄文件
cp $SOURCE/.env.example .env
cp $SOURCE/docker-compose.yml .

# 複製前端文件
cp $SOURCE/frontend/*.html frontend/
cp $SOURCE/frontend/*.js frontend/

# 複製後端文件
cp $SOURCE/backend/Dockerfile backend/
cp $SOURCE/backend/*.py backend/
cp $SOURCE/backend/requirements.txt backend/
cp -r $SOURCE/backend/alembic backend/

# 複製初始化腳本
cp $SOURCE/init-scripts/*.sql init-scripts/

# 複製 Nginx 配置
cp $SOURCE/nginx/nginx.conf nginx/
cp $SOURCE/nginx/conf.d/*.conf nginx/conf.d/

# 複製 MQTT 配置
cp $SOURCE/mosquitto/config/mosquitto.conf mosquitto/config/

# 複製 Prometheus 配置
cp $SOURCE/prometheus/prometheus.yml prometheus/
cp -r $SOURCE/prometheus/rules prometheus/

# 複製 Grafana 配置
cp -r $SOURCE/grafana/provisioning grafana/

# 複製 Loki 配置
cp $SOURCE/loki/loki-config.yml loki/
```

### 第 3 步：設置權限

```bash
# 設置文件權限
chmod 755 /opt/elitegets
chmod 644 /opt/elitegets/.env
chmod 644 /opt/elitegets/docker-compose.yml
chmod -R 755 /opt/elitegets/frontend
chmod -R 755 /opt/elitegets/backend
chmod -R 755 /opt/elitegets/init-scripts

# 設置數據目錄權限
chmod -R 777 /opt/elitegets/data
chmod -R 777 /opt/elitegets/logs
```

---

## 📋 文件放置檢查清單

```
根目錄:
☑️ .env.example
☑️ .env (複製自 .env.example)
☑️ docker-compose.yml

frontend/ 目錄:
☑️ meter-management-system-advance.html
☑️ meter-management-system-pro.html
☑️ meter-management-system-ultimate.html
☑️ meter-system-version-selector.html
☑️ electricity-bill-carbon-calculator.html
☑️ ai-electricity-analyzer.html
☑️ renewable-energy-detailed-system.html
☑️ building-configuration-system.html
☑️ charging-station-pure.html
☑️ main-dashboard-mobile.html
☑️ admin-dashboard-pure.html
☑️ all-versions-protected-template.html
☑️ universal-protection-system.js
☑️ developer-debug-mode.js
☑️ meter-adapter-engine.js

backend/ 目錄:
☑️ Dockerfile
☑️ requirements.txt
☑️ main.py
☑️ models.py
☑️ routes.py
☑️ database.py
☑️ auth.py
☑️ lstm-prediction-service.py
☑️ enterprise-integration.py
☑️ mqtt-bridge.js
☑️ license-protection-system.js
☑️ alembic/ (目錄及文件)

init-scripts/ 目錄:
☑️ 01-init.sql
☑️ 02-seed.sql (可選)

nginx/ 目錄:
☑️ nginx.conf
☑️ conf.d/default.conf
☑️ ssl/cert.pem (生產環境)
☑️ ssl/key.pem (生產環境)

mosquitto/ 目錄:
☑️ config/mosquitto.conf

prometheus/ 目錄:
☑️ prometheus.yml
☑️ rules/alerts.yml

grafana/ 目錄:
☑️ provisioning/datasources/prometheus.yml
☑️ provisioning/dashboards/ (目錄及文件)

loki/ 目錄:
☑️ loki-config.yml
```

---

## ✅ 驗證部署

```bash
# 檢查目錄結構
tree -L 2 /opt/elitegets

# 檢查文件是否都在
find /opt/elitegets -type f | wc -l

# 檢查權限
ls -la /opt/elitegets/
ls -la /opt/elitegets/frontend/ | head -5
ls -la /opt/elitegets/backend/ | head -5

# 驗證配置文件格式
docker-compose config

# 準備好了，開始部署！
docker-compose up -d
```

---

## 💡 常見問題

**Q: 文件放在不同目錄可以嗎？**
A: 可以，但需要修改 docker-compose.yml 中的 volumes 路徑

**Q: 如果目錄不存在會怎樣？**
A: Docker Compose 會自動創建，但建議提前創建以確保權限正確

**Q: 能否使用相對路徑？**
A: 推薦使用絕對路徑（/opt/elitegets）以避免問題

**Q: 數據目錄需要提前創建嗎？**
A: 不需要，Docker 會自動創建並管理

---

**現在您知道每個文件放在哪裡了！** ✅

**立即開始部署：**
```bash
mkdir -p /opt/elitegets
cd /opt/elitegets
cp /source/.env.example .env
# ... 複製其他文件 ...
docker-compose up -d
```
