import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import DeserializationError, UnknownAsset, UnprocessableTradePair
from rotkehlchen.exchanges.bitcoinde import Bitcoinde
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory
from rotkehlchen.utils.misc import ts_now

BITCOINDE_BALANCES_RESPONSE = """
{"data":{"balances":{"btc":{"total_amount":"0.5","available_amount":"0.5","reserved_amount":"0"},"bch":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"btg":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"eth":{"total_amount":"32.0","available_amount":"32.0","reserved_amount":"0"},"bsv":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"},"ltc":{"total_amount":"0.00000000000000000000","available_amount":"0","reserved_amount":"0"}},"encrypted_information":{"uid":"X","bic_short":"Y","bic_full":"Z"}},"errors":[],"credits":23}
"""


def test_name():
    exchange = Bitcoinde('a', b'a', object(), object())
    assert exchange.name == 'bitcoin.de'


def test_bitcoinde_query_balances_unknown_asset(function_scope_bitcoinde):
    """Test that if a bitcoinde balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    bitcoinde = function_scope_bitcoinde

    def mock_unknown_asset_return(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, BITCOINDE_BALANCES_RESPONSE)

    with patch.object(bitcoinde.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = bitcoinde.query_balances()

    assert msg == ''
    assert len(balances) == 6
    assert balances[A_ETH]['amount'] == FVal('32.0')
    assert balances[A_BTC]['amount'] == FVal('0.5')

    warnings = bitcoinde.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
