import pytest

from app.services.carbon import CarbonError, factor_for, scope2_tco2e


def test_industrial_2025_factor():
    f = factor_for(2025, "industrial")
    assert f.kg_per_kwh == 0.466
    assert f.factor_year == 2025
    assert f.provisional is False
    assert f.warnings == []
    assert f.source_url.startswith("https://www.moea.gov.tw/")


def test_residential_2025_factor():
    assert factor_for(2025, "residential").kg_per_kwh == 0.471


def test_later_year_uses_latest_as_provisional_with_warning():
    f = factor_for(2026, "industrial")
    assert f.kg_per_kwh == 0.466 and f.factor_year == 2025
    assert f.provisional is True
    assert f.warnings and "2026" in f.warnings[0]


def test_earlier_year_is_error_not_back_applied():
    with pytest.raises(CarbonError):
        factor_for(2024, "industrial")


def test_unknown_category_is_error():
    with pytest.raises(CarbonError):
        factor_for(2025, "commercial")


def test_scope2_rounds_to_three_decimals_without_truncation():
    # 1234.567 kWh * 0.466 / 1000 = 0.575 (0.57530...) -> 0.575
    assert scope2_tco2e(1234.567, 0.466) == 0.575
    # 1000 kWh * 0.467 / 1000 = 0.467 exactly (no int truncation to 0)
    assert scope2_tco2e(1000, 0.467) == 0.467
    # half-up at 3 decimals: 1.5 kWh*0.471/1000 = 0.0007065 -> 0.001
    assert scope2_tco2e(1.5, 0.471) == 0.001
    assert scope2_tco2e(0, 0.466) == 0.0
