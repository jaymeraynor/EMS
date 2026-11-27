from datetime import date

import pytest

from app.services.tariff import TariffBook, load_default_book, load_tariff_file, TariffError


@pytest.fixture(scope="module")
def book():
    return load_default_book()


def test_version_metadata(book):
    v = book.version_for(date(2026, 7, 1))
    assert v.version == "taipower-2025-10-01"
    assert v.effective_from == date(2025, 10, 1)
    assert v.effective_to is None
    assert v.source_url.startswith("https://www.taipower.com.tw/")
    assert v.verified_on == date(2026, 11, 27)


def test_no_version_before_effective_date(book):
    with pytest.raises(TariffError):
        book.version_for(date(2025, 9, 30))


# Literal values from regs 2.3 (high / extra-high; summer / non-summer)
def test_two_stage_high_summer(book):
    r = book.version_for(date(2026, 7, 1)).rates("high", "two_stage", True)
    assert (r.basic.regular, r.basic.non_summer, r.basic.sat_off) == (223.60, None, 44.70)
    assert (r.energy.peak, r.energy.sat_semi_peak, r.energy.off_peak) == (6.75, 2.77, 2.71)


def test_two_stage_high_non_summer(book):
    r = book.version_for(date(2026, 1, 1)).rates("high", "two_stage", False)
    assert (r.basic.regular, r.basic.non_summer, r.basic.sat_off) == (166.90, 166.90, 33.30)
    assert (r.energy.peak, r.energy.sat_semi_peak, r.energy.off_peak) == (6.37, 2.54, 2.46)


def test_two_stage_extra_high(book):
    v = book.version_for(date(2026, 1, 1))
    s = v.rates("extra_high", "two_stage", True)
    n = v.rates("extra_high", "two_stage", False)
    assert (s.basic.regular, s.basic.sat_off) == (217.30, 43.40)
    assert (s.energy.peak, s.energy.sat_semi_peak, s.energy.off_peak) == (6.17, 2.73, 2.55)
    assert (n.basic.regular, n.basic.non_summer, n.basic.sat_off) == (160.60, 160.60, 32.10)
    assert (n.energy.peak, n.energy.sat_semi_peak, n.energy.off_peak) == (5.79, 2.48, 2.28)


def test_three_stage_high_and_extra_high(book):
    v = book.version_for(date(2026, 1, 1))
    hs = v.rates("high", "three_stage", True)
    assert (hs.basic.regular, hs.basic.semi_peak, hs.basic.sat_off) == (223.60, 166.90, 44.70)
    assert (hs.energy.peak, hs.energy.semi_peak, hs.energy.sat_semi_peak, hs.energy.off_peak) \
        == (9.39, 5.85, 2.60, 2.53)
    hn = v.rates("high", "three_stage", False)
    assert hn.energy.peak is None
    assert (hn.energy.semi_peak, hn.energy.sat_semi_peak, hn.energy.off_peak) == (5.47, 2.41, 2.32)
    assert (hn.basic.regular, hn.basic.semi_peak, hn.basic.sat_off) == (166.90, 166.90, 33.30)
    es = v.rates("extra_high", "three_stage", True)
    assert (es.energy.peak, es.energy.semi_peak, es.energy.sat_semi_peak, es.energy.off_peak) \
        == (8.69, 5.38, 2.50, 2.40)
    assert (es.basic.regular, es.basic.semi_peak, es.basic.sat_off) == (217.30, 160.60, 43.40)
    en = v.rates("extra_high", "three_stage", False)
    assert (en.energy.semi_peak, en.energy.sat_semi_peak, en.energy.off_peak) == (5.03, 2.31, 2.18)
    assert (en.basic.regular, en.basic.semi_peak, en.basic.sat_off) == (160.60, 160.60, 32.10)


def test_loader_rejects_malformed_yaml(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: x\neffective_from: 2025-10-01\n")
    with pytest.raises(TariffError):
        load_tariff_file(bad)


def test_overlapping_versions_rejected(book):
    v = book.version_for(date(2026, 7, 1))
    with pytest.raises(TariffError):
        TariffBook([v, v])


def test_version_selected_by_date_when_two_versions(book):
    v1 = book.version_for(date(2026, 7, 1)).model_copy(update={"effective_to": date(2026, 7, 15)})
    v2 = v1.model_copy(update={"version": "next", "effective_from": date(2026, 7, 16),
                               "effective_to": None})
    b = TariffBook([v1, v2])
    assert b.version_for(date(2026, 7, 15)).version == "taipower-2025-10-01"
    assert b.version_for(date(2026, 7, 16)).version == "next"
