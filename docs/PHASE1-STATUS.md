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
2. 無資料的月份（coverage = 0）不視為「未用電」，不給 50% 基本電費折扣，只回警告。
3. 行業別調整係數只乘（基本＋流動），不乘超約附加費；功因調整對（基本＋流動）×係數計算，超約不給功因折扣。
4. 區段（相鄰讀數）超過 `MAX_GAP_MINUTES` 時，即使兩端有累計電能，其差值也不分配進任何時間窗（無法確定發生時點），因此會出現在 `gap_seconds`、並使該月 coverage < 1。
5. 區間度數 = 逐段累加（有兩端累計電能用差值並按時間線性內插，否則梯形），與「窗口兩端累計值相減」在連續資料時等價。
6. 讀數存取時間皆為 UTC；API 回應中需量區塊時間以 +08:00 表示。
7. 密碼下限 10 字元、上限 72 bytes（bcrypt 限制）。登入帳號不分大小寫（存小寫）。
8. 月帳單中途跨電價版本與跨季，以「（版本，季節）」為單位分段：流動電費逐日用該日版本/季節費率；基本電費與超約都按段計算（基本按日數比例，超約不比例）。
9. `seed-demo` 產生的讀數 source 記為 `api`，以 `is_demo` 與名稱「（模擬資料）」標示。

## 已知限制

- 月/年範圍的計算會把區間內所有讀數載入記憶體（年度碳排約 52 萬筆/分鐘取樣電表可行但偏重）；日後可改 SQL 彙總或預先聚合。
- 全部測試在沙盒內以 Postgres 17.12 與 SQLite 執行；未測 arm64 容器映像。
