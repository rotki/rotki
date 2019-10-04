import os

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_XMR
from rotkehlchen.typing import AssetMovementCategory, Location, TradeType


def test_cointracking_data_import(rotkehlchen_server):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    filepath = os.path.join(dir_path, 'data', 'cointracking_trades_list.csv')

    # Check that for unknown source we get an error
    response = rotkehlchen_server.import_data_from(source='other_source', filepath=filepath)
    assert response['result'] is False
    assert 'unknown location' in response['message']

    # Check that the test cointracking data are imported succesfully
    rotkehlchen_server.import_data_from(source='cointracking_info', filepath=filepath)
    trades = rotkehlchen_server.rotkehlchen.data.db.get_trades()
    asset_movements = rotkehlchen_server.rotkehlchen.data.db.get_asset_movements()
    warnings = rotkehlchen_server.rotkehlchen.msg_aggregator.consume_warnings()
    errors = rotkehlchen_server.rotkehlchen.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 3

    expected_trades = [Trade(
        timestamp=1566687660,
        location=Location.COINBASE,
        pair='ETH_EUR',
        trade_type=TradeType.BUY,
        amount=FVal('0.05772716'),
        rate=FVal('190.3783245183029963712055123'),
        fee=ZERO,
        fee_currency=A_ETH,
        link='',
        notes='',
    ), Trade(
        timestamp=1567418400,
        location=Location.EXTERNAL,
        pair='BTC_USD',
        trade_type=TradeType.BUY,
        amount=FVal('0.00100000'),
        rate=ZERO,
        fee=ZERO,
        fee_currency=A_BTC,
        link='',
        notes='Just a small gift from someone',
    )]
    assert expected_trades == trades

    expected_movements = [AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=1565848620,
        asset=A_XMR,
        amount=FVal('5'),
        fee_asset=A_XMR,
        fee=ZERO,
        link='',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=1566726120,
        asset=A_ETH,
        amount=FVal('0.05770427'),
        fee_asset=A_ETH,
        fee=ZERO,
        link='',
    )]
    assert expected_movements == asset_movements
