# 測試結果

日期：2026-11-27　Python 3.12.16（code review R4 修正後）

## PostgreSQL 17.12（TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/ems_test）
```
227 passed, 2 skipped
```

## SQLite（未設定 TEST_DATABASE_URL）
```
228 passed, 1 skipped
```
略過的 1 項是 `test_store_readings_waits_for_meter_row_lock`（需 Postgres 的列鎖，SQLite 的 `FOR UPDATE` 為 no-op）。

R1 新增測試：`backend/tests/test_review_r1.py`（15 項）。前端無自動測試（僅 `node --check`）。

R2 新增測試：`backend/tests/test_review_r2.py`（9 項）。前端與 nginx 設定無自動測試（僅 `node --check`；nginx 設定未實際載入驗證）。

R3 新增測試：`backend/tests/test_review_r3.py`（8 個測試函式、11 個案例含參數化；修正前 8 個案例失敗）。前端變更僅 `node --check`。

R4 新增測試：`backend/tests/test_review_r4.py`（19 個案例；修正前 16 個失敗，其餘為上限邊界與 9999 年已被未來時間檢查擋下的案例）。SQLite 略過 1 項（Postgres 列鎖測試）；Postgres 略過 2 項（SQLite 專屬的並行寫入與查詢計畫測試）。前端另以 node 腳本驗證不會 append(null)，並執行 `node --check`。
