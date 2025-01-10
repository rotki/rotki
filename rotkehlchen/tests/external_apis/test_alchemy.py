from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_EUR, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ApiKey,
    ChainID,
    ExternalService,
    ExternalServiceApiCredentials,
    Price,
    Timestamp,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.price import PriceHistorian


@pytest.mark.vcr(match_on=['alchemy_api_matcher'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_alchemy_historical_prices(price_historian: 'PriceHistorian', alchemy: 'Alchemy'):  # pylint: disable=unused-argument
    eur = A_EUR.resolve_to_asset_with_oracles()
    eth = A_ETH.resolve_to_asset_with_oracles()
    usd = A_USD.resolve_to_asset_with_oracles()
    dai = A_DAI.resolve_to_asset_with_oracles()

    # First query usd price
    price = alchemy.query_historical_price(
        from_asset=eth,
        to_asset=usd,
        timestamp=Timestamp(1597024800),
    )
    assert price == Price(FVal('394.3572783286'))

    # Query EUR price
    price = alchemy.query_historical_price(
        from_asset=eth,
        to_asset=eur,
        timestamp=Timestamp(1597024800),
    )
    assert price == Price(FVal('394.3572783286') * FVal('0.850618'))

    # Query an evm token
    price = alchemy.query_historical_price(
        from_asset=dai,
        to_asset=usd,
        timestamp=Timestamp(1597024800),
    )
    assert price == Price(FVal('1.018248283'))


@pytest.mark.vcr(match_on=['alchemy_api_matcher'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_alchemy_current_prices(price_historian: 'PriceHistorian', alchemy: 'Alchemy'):  # pylint: disable=unused-argument
    eth = A_ETH.resolve_to_asset_with_oracles()
    usd = A_USD.resolve_to_asset_with_oracles()
    dai = A_DAI.resolve_to_asset_with_oracles()

    price = alchemy.query_current_price(
        from_asset=eth,
        to_asset=usd,
    )
    assert price == Price(FVal('3425.0697715654'))

    price = alchemy.query_current_price(
        from_asset=dai,
        to_asset=usd,
    )
    assert price == Price(FVal('0.9990162355'))


@pytest.mark.vcr(match_on=['alchemy_api_matcher'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_alchemy_api_errors(
        price_historian: 'PriceHistorian',  # pylint: disable=unused-argument
        alchemy: 'Alchemy',
        database: 'DBHandler',
):
    usd = A_USD.resolve_to_asset_with_oracles()
    sample_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x3dBb91BDd5fc74c49146819ed58d7D204cf5a016'),
        chain_id=ChainID.ETHEREUM,
    )

    # fetch the current price of a token that is not supported.
    price = alchemy.query_current_price(
        from_asset=sample_token,
        to_asset=usd,
    )
    assert price == ZERO_PRICE

    # fetch the historical price of a token that is not supported.
    with pytest.raises(RemoteError, match='Token address not found'):
        alchemy.query_historical_price(
            from_asset=sample_token,
            to_asset=usd,
            timestamp=Timestamp(1697024800),
        )


@pytest.mark.vcr(match_on=['alchemy_api_matcher'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_alchemy_invalid_api_key(price_historian: 'PriceHistorian', database: 'DBHandler'):  # pylint: disable=unused-argument
    with database.user_write() as write_cursor:  # add the api key to the DB
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.ALCHEMY,
                api_key=(api_key := ApiKey('123totallyrealapikey123')),
            )],
        )

    alchemy = Alchemy(database=database)
    assert alchemy._get_api_key() == api_key
    with pytest.raises(RemoteError, match='Must be authenticated!'):
        alchemy.query_current_price(
            from_asset=A_ETH.resolve_to_asset_with_oracles(),
            to_asset=A_USD.resolve_to_asset_with_oracles(),
        )
