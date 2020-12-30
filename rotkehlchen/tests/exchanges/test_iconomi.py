import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import DeserializationError, UnknownAsset, UnprocessableTradePair
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.iconomi import Iconomi
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory
from rotkehlchen.utils.misc import ts_now

ICONOMI_BALANCES_RESPONSE = """
{"currency":"USD","daaList":[{"name":"CARUS-AR","ticker":"CAR","balance":"100.0","value":"1000.0"},{"name":"Strategy 2","ticker":"SCND","balance":"80.00000000","value":"0"}],"assetList":[{"name":"Aragon","ticker":"ANT","balance":"1000","value":"200.0"},{"name":"Ethereum","ticker":"ETH","balance":"32","value":"10000.031241234"},{"name":"Augur","ticker":"REP","balance":"0.5314532451","value":"0.8349030710000"}]}
"""

def test_name():
    exchange = Iconomi('a', b'a', object(), object())
    assert exchange.name == 'iconomi'


def test_iconomi_query_balances_unknown_asset(function_scope_iconomi):
    """Test that if a iconomi balance query returns unknown asset no exception
    is raised and a warning is generated. Same for unsupported assets"""
    iconomi = function_scope_iconomi

    def mock_unknown_asset_return(url, **kwargs):  # pylint: disable=unused-argument
        print("lol", url)
        return MockResponse(200, ICONOMI_BALANCES_RESPONSE)

    with patch.object(iconomi.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = iconomi.query_balances()

    assert msg == ''
    assert len(balances) == 3
    assert balances[A_ETH]['amount'] == FVal('32.0')
    assert balances[Asset('REP')]['amount'] == FVal('0.5314532451')

    warnings = iconomi.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unsupported ICONOMI strategy CAR' in warnings[0]
    assert 'unsupported ICONOMI strategy SCND' in warnings[1]
