# 測試結果

日期：2026-11-27　Python 3.12.16（code review R2 修正後）

## PostgreSQL 17.12（TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:5432/ems_test）
```
199 passed
```

## SQLite（未設定 TEST_DATABASE_URL）
```
198 passed, 1 skipped
```
略過的 1 項是 `test_store_readings_waits_for_meter_row_lock`（需 Postgres 的列鎖，SQLite 的 `FOR UPDATE` 為 no-op）。

R1 新增測試：`backend/tests/test_review_r1.py`（15 項）。前端無自動測試（僅 `node --check`）。

R2 新增測試：`backend/tests/test_review_r2.py`（9 項）。前端與 nginx 設定無自動測試（僅 `node --check`；nginx 設定未實際載入驗證）。
