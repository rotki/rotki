import os
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.externalapis.moralis import Moralis
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

# A timestamp for which Moralis should have DAI price data (2023-11-14).
DAI_TIMESTAMP = Timestamp(1700000000)


@pytest.fixture(name='moralis')
def fixture_real_moralis(database: 'DBHandler') -> Moralis:
    """A Moralis instance backed by a real API key taken from the environment.

    Skips the test if no MORALIS_API_KEY is set so the suite stays green in
    environments without credentials, while still exercising the live API when one
    is provided (mirrors the ETHERSCAN_API_KEY/BEACONCHAIN_API_KEY pattern).
    """
    if (api_key := os.environ.get('MORALIS_API_KEY')) is None:
        pytest.skip('No MORALIS_API_KEY provided in the environment')

    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.MORALIS,
                api_key=ApiKey(api_key),
            )],
        )
    return Moralis(database=database)


@pytest.mark.vcr
def test_moralis_historical_price(moralis: Moralis) -> None:
    """Query the real Moralis API for a historical DAI/USD price (a USD stablecoin,
    so the value should sit close to 1)."""
    price = moralis.query_historical_price(
        from_asset=A_DAI,
        to_asset=A_USD,
        timestamp=DAI_TIMESTAMP,
    )
    assert FVal('0.9') < price < FVal('1.1'), f'unexpected DAI historical price {price}'


@pytest.mark.vcr
def test_moralis_current_price(moralis: Moralis) -> None:
    """Query the real Moralis API for the current DAI/USD price."""
    price = moralis.query_current_price(
        from_asset=A_DAI.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert FVal('0.9') < price < FVal('1.1'), f'unexpected DAI current price {price}'


def test_moralis_unsupported_asset(moralis: Moralis) -> None:
    """Native ETH is not an erc20 token, so Moralis cannot price it. This is resolved
    locally before any network call."""
    eth = A_ETH.resolve_to_asset_with_oracles()
    usd = A_USD.resolve_to_asset_with_oracles()

    assert moralis.query_current_price(from_asset=eth, to_asset=usd) == ZERO_PRICE
    with pytest.raises(NoPriceForGivenTimestamp):
        moralis.query_historical_price(
            from_asset=eth,
            to_asset=usd,
            timestamp=DAI_TIMESTAMP,
        )
