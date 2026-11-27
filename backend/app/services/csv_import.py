"""CSV parsing for manual reading import. Header: ts,power_kw[,energy_kwh_total,kvarh_total]."""
from __future__ import annotations

import csv
import io

from pydantic import ValidationError

from app.schemas import ReadingIn

REQUIRED = ("ts", "power_kw")
ALLOWED = ("ts", "power_kw", "energy_kwh_total", "kvarh_total")
MAX_LISTED_ERRORS = 100


class CsvFormatError(ValueError):
    """File-level problem (bad header, empty file...)."""


class CsvRowErrors(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__(f"{len(errors)} invalid row(s)")
        self.errors = errors


def _first_error(exc: ValidationError) -> str:
    e = exc.errors()[0]
    loc = ".".join(str(x) for x in e["loc"])
    return f"{loc}: {e['msg']}" if loc else e["msg"]


def parse_csv(raw: bytes) -> tuple[list[ReadingIn], list[int]]:
    """Return (readings, their file line numbers), or raise CsvFormatError / CsvRowErrors (row = file line number)."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFormatError("檔案必須為 UTF-8 編碼") from exc
    reader = csv.reader(io.StringIO(text))
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise CsvFormatError("檔案是空的") from None
    except csv.Error as exc:
        raise CsvFormatError(f"CSV 格式錯誤（第 1 行）：{exc}") from None
    if not all(c in header for c in REQUIRED) or any(c not in ALLOWED for c in header) \
            or len(set(header)) != len(header):
        raise CsvFormatError("標題列必須是 ts,power_kw[,energy_kwh_total,kvarh_total]")

    items: list[ReadingIn] = []
    rows: list[int] = []
    errors: list[dict] = []
    while True:
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:       # e.g. field larger than csv.field_size_limit
            raise CsvRowErrors(errors[:MAX_LISTED_ERRORS - 1]
                               + [{"row": reader.line_num, "error": f"CSV 格式錯誤：{exc}"}]) from None
        line_no = reader.line_num
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) != len(header):
            errors.append({"row": line_no, "error": f"欄位數 {len(row)} 與標題列 {len(header)} 不符"})
            continue
        data = {h: (c.strip() or None) for h, c in zip(header, row)}
        try:
            items.append(ReadingIn.model_validate(data))
            rows.append(line_no)
        except ValidationError as exc:
            errors.append({"row": line_no, "error": _first_error(exc)})
    if errors:
        raise CsvRowErrors(errors[:MAX_LISTED_ERRORS])
    if not items:
        raise CsvFormatError("檔案沒有資料列")
    return items, rows
