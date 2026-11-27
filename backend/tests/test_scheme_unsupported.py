import pytest
from tests.test_bill import meter, month_samples
from app.services.billing import compute_bill


def test_bill_for_unsupported_scheme_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        compute_bill(meter(scheme="batch_production"), month_samples(2026, 7), "2026-07")
