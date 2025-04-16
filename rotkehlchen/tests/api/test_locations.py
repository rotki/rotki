from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_EUR
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.tests.utils.exchanges import mock_exchange_data_in_db
from rotkehlchen.types import (
    EVM_LOCATIONS_TYPE,
    ChecksumEvmAddress,
    Location,
    Price,
    Timestamp,
    TradeType,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

UNISWAP_ADDR = string_to_evm_address('0xcaf012cB72f2c7152b255E091837E3a628F739e7')


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('ethereum_accounts', [[UNISWAP_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_associated_locations(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        added_exchanges: list[EVM_LOCATIONS_TYPE],
        ethereum_accounts: list[ChecksumEvmAddress],  # pylint: disable=unused-argument
        start_with_valid_premium: bool,  # pylint: disable=unused-argument
) -> None:
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    mock_exchange_data_in_db(added_exchanges, rotki)
    db = rotki.data.db
    with db.user_write() as cursor:
        db.add_trades(
            write_cursor=cursor,
            trades=[Trade(
                timestamp=Timestamp(1595833195),
                location=Location.NEXO,
                base_asset=A_ETH,
                quote_asset=A_EUR,
                trade_type=TradeType.BUY,
                amount=FVal('1.0'),
                rate=Price(FVal('281.14')),
                fee=ZERO,
                fee_currency=A_EUR,
                link='',
                notes='',
            )])

    # get locations
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'associatedlocations',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert set(result) == {'nexo', 'binance', 'poloniex'}
