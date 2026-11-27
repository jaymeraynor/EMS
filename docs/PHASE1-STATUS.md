# Phase 1 狀態（prod-foundation）

更新日期：2026-11-27

## 九大項目

| # | 項目 | 狀態 | 剩餘 / 備註 |
|---|---|---|---|
| 1 | 持久化（PostgreSQL、SQLAlchemy 2、Alembic） | **完成** | 初始 migration 與 models 比對無差異（測試：upgrade → compare_metadata → downgrade，Postgres 與 SQLite 皆通過）。readings 不自動刪除，保存期限 ≥ 1 年僅為文件約定，尚無備份/封存機制。 |
| 2 | 認證與隔離 | **完成** | JWT HS256、bcrypt、三種角色、跨組織一律 404、無公開註冊、CORS 由環境變數控制。尚無：密碼重設、登入失敗鎖定/速率限制、Token 撤銷（僅靠 60 分鐘到期與停用帳號）。 |
| 3 | 電表資料接入 | **完成** | API key（sha256）、`/ingest` 驗證、CSV 匯入、讀數查詢分頁、`ingest_batches` 稽核。尚無：ingest 速率限制、API key 到期機制。 |
| 4 | 計算服務 | **部分** | 度數積分、Taipei 日、15 分鐘需量、TOU、電價版本、月帳單（二段式/三段式固定）、功因、超約、碳排皆完成並有測試。未做：尖峰可變動、批次生產（拋 NotImplementedError）、高壓供電低壓計量換算、161kV/345kV 折扣、儲冷空調、最低契約容量 100 kW 檢核。多項規則待核實，見下方 TODO。 |
| 5 | API 面 | **完成** | 規格列出的端點皆有；假預測/異常端點已移除，`/forecast` 回 501。 |
| 6 | 前端 | **完成（未經瀏覽器實測）** | 三頁、無 CDN、所有 API 字串經 textContent。本沙盒沒有瀏覽器，僅做 `node --check` 語法檢查與 API 煙霧測試，**尚未在實際瀏覽器目視驗證**。 |
| 7 | Docker | **部分** | Dockerfile、compose、nginx 已寫好且 YAML 可解析；沙盒沒有 docker / nginx，**尚未實際 build / up**。後端的啟動流程（alembic upgrade → uvicorn、production 模式）已在本機以 Postgres 煙霧測試過。 |
| 8 | 測試 | **完成** | 見 `backend/TEST_RESULTS.md`。 |
| 9 | CI | **完成（未在 GitHub 上實跑）** | `.github/workflows/ci.yml` 已寫好；未 push，故尚未實際執行。 |

## TODO 資料欄位 / 值為 null 或待核實（共同來源：`regs/tw-energy-regs-2026-11-27.md`）

| 欄位 / 規則 | 位置 | 現況 |
|---|---|---|
| 行業別電價調整係數 | `meters.industry_adjustment_coef`（nullable） | null → 以 1.0 計算，帳單 warnings 標「TODO」。需依客戶電費單行業別填入（regs §2.3、§7-6）。 |
| 離峰日日曆 | `data/offpeak_days.yaml` `days: []` | 空。國定假日暫以一般平日/週六計價，帳單 warnings 標「TODO」（regs §7-5）。 |
| 跨季基本電費 | `services/billing.py` | 暫以日數比例；帳單 assumptions 帶「TODO: 台電跨季基本電費計算方式未核實，暫以日數比例」。同一規則也用於跨電價版本的月份。 |
| 跨季超約附加費 | `services/billing.py` | 規則文字只說超約按月計，跨季處理 regs 未載。暫以各段（版本，季節）各自的最高需量算超約，再乘日數比例；帳單 assumptions 帶「TODO: 台電跨季超約附加費計算方式未核實，暫以日數比例」。每個 items 列含 `segment_days`、`segment_amount`（未比例金額）與比例後 `amount`。 |
| 功率因數適用條件 | `services/billing.py` | kVARh 有效區間（兩端皆有讀數且未超過間隔上限）必須涵蓋全部 kWh 已涵蓋的區間，否則不調整（避免把「沒量到」當成 0 kVARh 而給最高 1.5% 折扣），並於 warnings 說明。 |
| 計費期間 | `services/billing.py` | 以 Asia/Taipei 日曆月；台電實際依抄表日（assumptions 標 TODO）。 |
| 超約附加費單價 | `services/billing.py` `over_contract` | 規定未明載，暫用：尖峰→經常契約單價；半尖峰→半尖峰契約單價；週六半尖峰/離峰→週六半尖峰/離峰契約單價。帳單 assumptions 標示。 |
| 夏月累計契約容量 | 同上 | 夏月不把「非夏月契約」計入累計契約容量（非夏月契約只在非夏月存在）。 |
| 超約不重複的扣除基準 | 同上 | 扣除「較高優先時段的原始超約量」（raw excess）而非已扣除後的淨值；規定文字較含糊。 |
| 功率因數整數點數 | `power_factor_adjustment` | 取 PF×100 無條件捨去為整數點；規定未載取整方式。帳單 assumptions 標示。 |
| 排碳係數 | `data/emission_factors.yaml` | 只有 2025（114 年度）；2024（113 年度 0.474）僅見搜尋摘要未核實，故不收錄 → 查 2024 回 422。2026 以上以 2025 係數暫代並標 provisional。綠電以 0 計（regs 未核實）未實作。 |
| 電價版本 | `data/tariffs/taipower-2025-10-01.yaml` | 2026-12 第 3 次審議若調價，2027-01-01 起需新增版本檔。尖峰可變動、批次生產費率未收錄。 |
| 電表計量點 | — | 高壓供電以低壓電表計量的換算（regs §2.7）未實作。 |

## 設計決定（開放給日後覆議）

1. `effective_to` 為**含當日**的最後一天（null = 無期限）；版本不得重疊。
2. 只有資料覆蓋率 100% 的月份才可能視為「未用電」並給 50% 基本電費折扣；無資料或部分覆蓋的月份不給折扣，只回警告（R1 前只要 coverage > 0 即給）。
3. 行業別調整係數只乘（基本＋流動），不乘超約附加費；功因調整對（基本＋流動）×係數計算，超約不給功因折扣。
4. 區段（相鄰讀數）超過 `MAX_GAP_MINUTES` 時，即使兩端有累計電能，其差值也不分配進任何時間窗（無法確定發生時點），因此會出現在 `gap_seconds`、並使該月 coverage < 1。
5. 區間度數 = 逐段累加（有兩端累計電能用差值並按時間線性內插，否則梯形），與「窗口兩端累計值相減」在連續資料時等價。
6. 讀數存取時間皆為 UTC；API 回應中需量區塊時間以 +08:00 表示。
7. 密碼下限 10 字元、上限 72 bytes（bcrypt 限制）。登入帳號不分大小寫（存小寫）。
8. 月帳單中途跨電價版本與跨季，以「（版本，季節）」為單位分段：流動電費逐日用該日版本/季節費率；基本電費與超約附加費都按段計算並乘「該段日數 / 當月日數」（R1 前超約未比例，跨季月份會重複計收，已修正）。
9. `seed-demo` 產生的讀數 source 記為 `api`，以 `is_demo` 與名稱「（模擬資料）」標示。

## Code review R1 處理紀錄

全部 10 項皆已查證並修正，無不同意項目。行為變更皆先寫失敗測試（`backend/tests/test_review_r1.py`）。

- 累計讀數並行驗證：`store_readings` 先對電表列 `SELECT … FOR UPDATE`（SQLite 為 no-op），鎖持有至 commit。Postgres 有真實執行緒測試（他人持鎖時寫入者必須等待；SQLite 略過該測試，另有編譯語句順序測試）。
- 功因需 kVARh 覆蓋、零用電需完整覆蓋、跨季超約按日數比例：見上方 TODO 表與設計決定。
- 組織碳排：先加總未四捨五入值（各電表用自己的係數），最後半進位一次。
- CSV 匯入改為同步路由（FastAPI 以執行緒池執行）；`csv.Error`（欄位超過 131072 字元）轉為 422。
- docker-compose 改傳 `POSTGRES_HOST/USER/PASSWORD/DB`，由 `app.config.resolve_database_url` 以 `URL.create` 組 URL（密碼含 `@ : / #` 皆可）；`DATABASE_URL` 若有設定仍優先。Alembic 同用此函式。注意 compose 本身對 `.env` 值中的 `$` 仍會做變數插值（需寫成 `$$`）。尚未實際 `docker compose up` 驗證。
- 前端：儀表板與電費頁以請求世代計數，過期回應不渲染；無電表時清空所有指標與圖表；電費與碳排共用同一世代。僅 `node --check` 與人工檢視，**沒有瀏覽器測試**（無對應自動測試）。

## Code review R2 處理紀錄

7 項皆已查證並修正，無不同意項目。後端行為變更皆先寫失敗測試（`backend/tests/test_review_r2.py`，修正前 8 項失敗）。

- CSV 嚴格解析：`csv.reader(strict=True)`，結尾未閉合引號（如 `"123`）現在回 422 且不寫入。
- 月份範圍：`month_window` 對無法表示的月份丟 `ValueError`，帳單路由回 422。查證時發現 `0001-01` 也會失敗（轉 UTC 時 `OverflowError`，不只審查提到的 `0000-01`、`9999-12`），一併處理。碳排年份已限制 2000–2100，不受影響。
- 佔位密鑰：非 `test` 環境下，`JWT_SECRET` 或資料庫密碼（`POSTGRES_PASSWORD` 或 `DATABASE_URL` 內密碼）含 `change-me`（不分大小寫）即拒絕啟動。比審查要求的「等於範例值」更寬，因為 `.env.example` 的值本身就含此字串。
- 前端 `taipeiToday()` 改用 `formatToParts` 組 `YYYY-MM-DD`。電表挑選器加請求世代檢查，切換站點時立即清空電表與結果（`onChange` 以空清單觸發），過期的 `/meters` 回應被丟棄。僅 `node --check` 與人工檢視，**沒有瀏覽器測試**。
- nginx：`/api/` 改用 `resolver 127.0.0.11` 加變數 `proxy_pass`，每次請求（DNS 快取 10 秒）重新解析 `api`，容器換 IP 不需重載。上傳大小改為 `/api/` 11m（含 multipart 開銷）、其餘 1m；後端仍精確檢查 10 MiB 檔案限制。**未實際載入 nginx 或 `docker compose up` 驗證**；`127.0.0.11` 假設使用 Compose 預設的使用者自訂網路。

## 已知限制

- 月/年範圍的計算會把區間內所有讀數載入記憶體（年度碳排約 52 萬筆/分鐘取樣電表可行但偏重）；日後可改 SQL 彙總或預先聚合。
- 全部測試在沙盒內以 Postgres 17.12 與 SQLite 執行；未測 arm64 容器映像。

## Code review R3 處理紀錄

7 項 + 1 項 lead 煙霧測試備註皆已查證。後端行為變更先寫失敗測試（`backend/tests/test_review_r3.py`，修正前 8 項失敗）。

- 切換據點立即清空（前端）：`loadMeters` 在清空電表選項後立即呼叫 `onChange()`，面板清空並使進行中的試算失效（沿用各頁的 generation 機制）。
- 載入電表失敗顯示錯誤（前端）：`/meters` 失敗時顯示錯誤，且僅在該請求仍屬於目前選取的據點時才顯示。
- 稀疏 ingest 查詢（後端）：重複偵測改為只查「本批次的確切時間戳」（每 500 筆一組 `IN`）；累計讀數檢查改為每筆新資料只查前後各一筆已存資料，不再載入整段歷史。代價是最壞情況每個暫存器欄位每筆 2 次索引查詢（5000 筆上限內），換取記憶體與鎖持有時間與歷史長度無關。有測試確認稀疏批次不執行無 LIMIT 的範圍掃描，且違規偵測與重複計數行為不變。
- 讀數量級上限（後端）：`power_kw ≤ 1e7`、累計 kWh/kvarh ≤ 1e12，API 與 CSV 共用 `ReadingIn`，超過回 422。上限為實務值（10 GW、1e12 kWh），是我的判斷，審查未指定數字。
- 日期範圍（後端）：`daily`、`demand`、site `summary` 的日期窗口無法表示（如 `0001-01-01`、`9999-12-31`）時回 422。
- CORS（後端）：允許標頭加入 `X-API-Key`，並有預檢測試。
- 開發用 `/docs`：**部分不同意審查建議，採用指示的最簡做法**。未在 nginx 代理 `/docs`、`/openapi.json`，因為 Swagger UI 需載入 CDN 資產，會被 nginx 的 CSP 擋下，放寬 CSP 不值得；改在 README 記載開發時用 `docker compose exec` 或暫時發佈 api 連接埠存取。
- 煙霧測試備註（前端）：圖表單位標籤與最上方刻度重疊 → 上邊界由 10 增為 24；電表名稱已含「模擬」時不再附加「（模擬）」。已確認 JS 與 HTML 沒有 `style` 屬性或 `setAttribute('style', …)`，SVG 僅使用呈現屬性（fill、stroke 等），不受 `style-src 'self'` 影響。前端無自動測試（僅 `node --check`），未做瀏覽器重測。


## Code review R4 處理紀錄

7 項皆已處理，先寫失敗測試（`backend/tests/test_review_r4.py`，修正前 16 個案例失敗）。

- 登入表單（P1）：`<form method="post" action="index.html">`，送出鈕預設 `disabled`，`app.js` 安裝 submit handler 後才啟用；JS 載入失敗時帳密不會進入網址（最壞情況 nginx 對靜態頁 POST 回 405，這是可接受的）。pytest 解析 HTML 驗證。
- SQLite 並行寫入（P2）：`_lock_meter` 在 SQLite 上先執行 `BEGIN IMMEDIATE` 取得寫入鎖再驗證，驗證與寫入成為一個序列化單元（Postgres 仍用列鎖）。以兩個連線/執行緒的測試驗證第二批會被拒絕。
- 部分索引（P2）：`readings(meter_id, ts) WHERE energy_kwh_total IS NOT NULL` 與 `... kvarh_total IS NOT NULL`（模型 + migration `0002`，含 downgrade）；查詢條件 `col IS NOT NULL` 與索引述詞一致，以 SQLite `INDEXED BY` 驗證可用。原有完整索引保留供其他查詢使用。
- 契約容量／係數上限（P2）：各契約容量 ≤ 1,000,000 kW（1 GW）、行業別調整係數 ≤ 10；建立與更新皆套用。以最大值建表並以 1e7 kW 讀數試算電費，回 200；超過回 422。上限為我的判斷值。
- 組織 Scope 2（P2）：頂層 `kwh`、`scope2_tco2e` 僅計入真實電表；模擬電表另列 `simulated_total_kwh`、`simulated_total_emissions`。前端目前未顯示組織層級總計，無需變更。
- 時間戳（P3）：`ReadingIn` 驗證器先轉 UTC，超出 datetime 範圍者回 422（API）／列錯誤（CSV），不再 500。
- 前端 append(null)（P3）：`notes()` 回傳 null 時不再 append（碳排與電費兩處）；以 node 腳本模擬 DOM 驗證，並通過 `node --check`。


## Code review R5 處理紀錄

- [P1] 已修正：兩段式超約的週六半尖峰／離峰累計門檻改為 經常+非夏月+週六半尖峰（+離峰），夏月與非夏月皆然；非夏月契約僅自夏月平日尖峰門檻排除（尖峰：夏月=經常、非夏月=經常+非夏月）。三段式維持 經常+半尖峰+…（三段式無非夏月契約，`basic_charge` 亦忽略之，故「同理加入半尖峰」解讀為以半尖峰取代非夏月）。10% 分段以各時段修正後的累計契約計算；不重複扣除仍用各時段原始超約量。測試：`backend/tests/test_review_r5.py`（修正前 3 個失敗）。
- 未處理（open）：
  - [P2] 大型 CSV 匯入應批次查詢電表暫存器（目前無列數上限，每列每暫存器 2 次查詢且持有電表鎖）。
  - [P2] 時間戳應要求明確時區（`AwareDatetime` 仍接受 Unix epoch 數字／數字字串）。
  - [P3] README 管理員初始化以命令列 `--password` 傳密碼，且範例 9 字元不符 10 字元下限。
