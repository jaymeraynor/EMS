# EMS 能源管理系統（prod-foundation，Phase 1）

高壓／特高壓用戶的用電資料收集、需量、電費試算與範疇二碳排。這是「可上線的基礎版」：資料落地 PostgreSQL、
有登入與組織隔離、計算邏輯有單元測試。舊的展示原型已移到 `legacy/`（未維護，不部署）。

## 架構

```
backend/    FastAPI + SQLAlchemy 2 + Alembic（PostgreSQL 17；測試亦可用 SQLite）
frontend/   純 HTML/JS/CSS（無 CDN），由 nginx 提供並反向代理 /api/
deploy/     nginx.conf
legacy/     舊展示原型（不部署）
docs/       PHASE1-STATUS.md（完成度與 TODO 清單）
```

## 啟動（Docker）

```bash
cp .env.example .env          # 填入 POSTGRES_PASSWORD、JWT_SECRET（>= 32 字元）
docker compose up -d --build  # api 啟動時會自動 alembic upgrade head
docker compose exec api python -m app.cli create-admin --email you@example.com --password '至少10字元的密碼'
# 選用：建立「模擬資料」示範電表
docker compose exec api python -m app.cli seed-demo
```

開啟 http://127.0.0.1:8080 （只綁定 127.0.0.1；對外請在前面加 TLS 反向代理）。DB 與 API 不對外開放埠。

## 本機開發與測試

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                                            # 預設用 SQLite
TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/ems_test pytest -q   # PostgreSQL
```

## 環境變數

| 變數 | 說明 | 預設 |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy URL（`postgresql+psycopg://…`） | `sqlite:///./ems.db`（僅開發） |
| `JWT_SECRET` | HS256 金鑰，**必填且 ≥ 32 字元**，否則服務拒絕啟動（`EMS_ENV=test` 除外） | — |
| `EMS_ENV` | `production` / `development` / `test`。production 會關閉 /docs | `production` |
| `JWT_EXPIRE_MINUTES` | Token 有效分鐘 | `60` |
| `CORS_ORIGINS` | 允許的跨來源，逗號分隔；預設不允許（nginx 同源） | 空 |
| `INGEST_MAX_FUTURE_SKEW_S` | 讀數時間戳允許比現在晚幾秒 | `120` |
| `MAX_GAP_MINUTES` | 相鄰讀數間隔超過此值不積分，視為缺資料 | `15` |
| `MAX_CSV_BYTES` | CSV 上限 | `10485760`（10 MB） |
| `BCRYPT_ROUNDS` | bcrypt cost | `12` |
| `POSTGRES_USER/PASSWORD/DB`, `WEB_PORT` | 僅 docker-compose 使用 | 見 `.env.example` |

## 角色

| 角色 | 權限 |
|---|---|
| `admin` | 全部組織；建立組織與使用者（含其他 admin）；由 CLI 建立第一位 |
| `org_admin` | 只限自己組織：管理案場／電表／使用者（不能建 admin）、匯入 CSV |
| `viewer` | 自己組織唯讀 |

沒有公開註冊。存取他組織的案場／電表／使用者一律回 **404**（不洩漏是否存在）。

## 電表資料上傳 API

1. `POST /api/v1/meters`（org_admin/admin）建立電表，回應中的 `api_key`（`ems_…`）**只顯示一次**，資料庫只存 sha256。遺失請 `POST /api/v1/meters/{id}/rotate-key`。
2. 裝置端：

```http
POST /api/v1/ingest
X-API-Key: ems_xxxxxxxx
Content-Type: application/json

{"readings":[{"ts":"2026-07-01T08:00:00+08:00","power_kw":123.4,"energy_kwh_total":98765.4,"kvarh_total":23456.7}]}
```

- API key 決定電表（body 沒有 meter_id）。`ts` 必須帶時區；`power_kw`、`energy_kwh_total`、`kvarh_total` 皆須為有限且 ≥ 0 的數字；單次最多 5000 筆；
  時間不可晚於現在 + `INGEST_MAX_FUTURE_SKEW_S`。
- 累計電能（`energy_kwh_total`、`kvarh_total`）不可倒退（與已存資料及同批資料比較），違反回 422 並指出第幾筆（`{"item": n, "error": …}`）。
- 重複（同電表同時間）不報錯，略過並計數。回應 `{"received":…, "inserted":…, "duplicates":…}`。金鑰無效 → 401。
- 查詢：`GET /api/v1/meters/{id}/readings?start=&end=&limit=&offset=`（limit 最大 10000，區間 [start,end)）。

### CSV 匯入

`POST /api/v1/meters/{id}/readings/csv`（multipart 欄位 `file`，org_admin/admin，上限 10 MB，UTF-8）。標題列：

```csv
ts,power_kw,energy_kwh_total,kvarh_total
2026-07-01T08:00:00+08:00,123.4,98765.4,23456.7
```

只有前兩欄也可（`ts,power_kw`）。任何一列有誤即**整份不匯入**，回 422 與錯誤清單 `[{"row": 列號, "error": …}]`（最多 100 筆；列號 = 檔案行號，標題為第 1 行）。

## 其他 API（皆在 `/api/v1`）

`health`、`auth/login`（OAuth2 password form）、`auth/me`、`orgs`、`users`、`sites`、`meters`（含 PATCH 契約容量/電價欄位）、
`meters/{id}/daily?start=&end=`、`meters/{id}/demand?date=`、`sites/{id}/summary?date=`、`meters/{id}/bill?month=YYYY-MM`、
`meters/{id}/scope2?year=`、`orgs/{id}/scope2?year=`。互動文件：非 production 環境 `/docs`。
`GET /forecast` 回 501「未啟用」。

## 計算方式摘要

- **度數**：兩筆讀數間的累計電能差（兩端都有時），否則 `power_kw` 梯形積分；依實際時間差加權，不假設固定取樣間隔；
  超過 `MAX_GAP_MINUTES` 的區段不積分，並回報 `gap_seconds` 與 `coverage`。
- **日**：Asia/Taipei 日曆日。**需量**：Taipei :00/:15/:30/:45 對齊的 15 分鐘區塊，度數 ×4；資料不完整的區塊標 `complete=false`，不納入最高需量。
- **時段／電價／基本電費／超約／功因**：數字全部來自 `backend/app/data/*.yaml`（內含來源 URL 與查證日期），公式見 `backend/app/services/billing.py` 的 docstring。
- **碳排**：kWh × 係數 ÷ 1000，四捨五入到 3 位；係數依「排放年度 × 用戶類別」，不以新年度回推舊年度。

## 模擬／未啟用／待核實

- **模擬資料**：`seed-demo` 建立的電表 `is_demo = true`，前端顯示紅色「模擬資料」標記。
- **未啟用**：用電預測（`/forecast` 501）、異常偵測（已移除假端點）。
- **未實作**：三段式尖峰可變動、批次生產電價（呼叫會 `NotImplementedError` / API 501）、高壓供電低壓計量換算與 161kV/345kV 折扣（regs §2.7）。
- **TODO / 待核實**（完整清單見 `docs/PHASE1-STATUS.md`）：行業別電價調整係數預設 1.0（TODO）、離峰日日曆為空（TODO）、跨季基本電費以日數比例（TODO）、計費期間用日曆月而非抄表日。
  帳單上會顯示這些警告與假設。
- 電價 2027-01-01 起可能調整：新增一份 `data/tariffs/*.yaml`（填 `effective_from`，並把舊檔 `effective_to` 設為前一天）即可，歷史月份不受影響。

## 資料保存

`readings` 不會被自動刪除；規劃至少保存 1 年（能源申報須能追溯原始電表資料）。若日後需要清理，請以人工、有稽核的方式進行；`ingest_batches` 為匯入稽核紀錄。
