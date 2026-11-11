import pytest

from rotkehlchen.assets.asset import FiatAsset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_EUR, A_USD
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.frankfurter import (
    get_current_frankfurter_exchange_rates,
    get_historical_frankfurter_exchange_rates,
)
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_CNY
from rotkehlchen.types import Timestamp


@pytest.mark.vcr
def test_get_current_frankfurter_exchange_rates() -> None:
    rates_map = get_current_frankfurter_exchange_rates(A_USD.resolve_to_fiat_asset())
    assert {A_EUR, A_CNY} <= rates_map.keys()
    assert all(asset.is_fiat() and price > ZERO for asset, price in rates_map.items())


@pytest.mark.vcr
def test_get_historical_frankfurter_exchange_rates() -> None:
    rates_map = get_historical_frankfurter_exchange_rates(
        from_asset=(eur := A_EUR.resolve_to_fiat_asset()),
        time=Timestamp(1762776000),  # Monday 2025-11-10 12:00 UTC
    )
    # ECB reference rate of the day
    assert rates_map[(usd := A_USD.resolve_to_fiat_asset())] == FVal('1.1571')
    assert all(asset.is_fiat() and price > ZERO for asset, price in rates_map.items())

    # a weekend day has no ECB rates and gets the rates of the previous business day
    assert get_historical_frankfurter_exchange_rates(
        from_asset=eur,
        time=Timestamp(1762603200),  # Saturday 2025-11-08 12:00 UTC
    )[usd] == FVal('1.1561')  # rate of Friday 2025-11-07


@pytest.mark.vcr
def test_frankfurter_unsupported_currency() -> None:
    with pytest.raises(RemoteError):  # no ECB reference rates are published for NGN
        get_current_frankfurter_exchange_rates(FiatAsset('NGN'))
