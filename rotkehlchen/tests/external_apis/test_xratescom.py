import pytest

from rotkehlchen.constants.assets import A_EUR, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.xratescom import (
    get_current_xratescom_exchange_rates,
    get_historical_xratescom_exchange_rates,
)
from rotkehlchen.tests.utils.constants import A_CNY


def test_get_current_xratescom_exchange_rates():
    rates_map = get_current_xratescom_exchange_rates(A_USD.resolve_to_fiat_asset())
    for asset, price in rates_map.items():
        assert asset.is_fiat()
        assert price is not None and price > ZERO

    rates_map = get_current_xratescom_exchange_rates(A_CNY.resolve_to_fiat_asset())
    for asset, price in rates_map.items():
        assert asset.is_fiat()
        assert price is not None and price > ZERO


def test_get_historical_xratescom_exchange_rates():

    rates_map = get_historical_xratescom_exchange_rates(
        from_asset=A_USD.resolve_to_asset_with_oracles(),
        time=1459585352,
    )
    for asset, price in rates_map.items():
        assert asset.is_fiat()
        assert price is not None and price > ZERO
        if asset == A_CNY:
            usd_cny_price = price

    rates_map = get_historical_xratescom_exchange_rates(
        from_asset=A_CNY.resolve_to_asset_with_oracles(),
        time=1459585352,
    )
    for asset, price in rates_map.items():
        assert asset.is_fiat()
        assert price is not None and price > ZERO
        if asset == A_USD:
            cny_usd_price = price

    assert cny_usd_price.is_close(1 / usd_cny_price)

    with pytest.raises(RemoteError):
        get_historical_xratescom_exchange_rates(
            from_asset=A_EUR.resolve_to_asset_with_oracles(),
            time=512814152,
        )
