import pytest

from rotkehlchen.app_upgrades.manager import RotkiUpgradeManager
from rotkehlchen.constants.assets import A_ETH, A_BTC
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.tests.utils.exchanges import create_test_binance
from rotkehlchen.typing import (
    Location,
    AssetAmount,
    Fee,
    Price,
    Timestamp,
    TradeType,
)


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX, Location.KRAKEN)])  # noqa: E501
def test_upgrade_1(rotkehlchen_api_server_with_exchanges, added_exchanges):
    """
    Test that the first app upgrade for rotki works. This update removes information about some
    exchanges when there is more than one instance or if it is kraken.

    In the test we setup instances of the exchanges to trigger the updates and one exchange
    (POLONIEX) that shouldn't be affected.
    """
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    db = rotki.data.db
    # Since we have initialized the rotkehlchen object the migration has already run
    # and the setting has been updated. Let's reset this setting to what the user would experience
    db.conn.cursor().execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('last_app_upgrade', 0),
    )
    # Add trades and update reanges in both exchanges
    for exchange_location in added_exchanges:
        db.add_trades([Trade(
            timestamp=Timestamp(1),
            location=exchange_location,
            base_asset=A_BTC,
            quote_asset=A_ETH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(1)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_ETH,
            link='foo',
            notes='boo',
        )])
        db.update_used_query_range(name=f'{str(exchange_location)}_trades', start_ts=0, end_ts=9999)  # noqa: E501
        db.update_used_query_range(name=f'{str(exchange_location)}_margins', start_ts=0, end_ts=9999)  # noqa: E501
        db.update_used_query_range(name=f'{str(exchange_location)}_asset_movements', start_ts=0, end_ts=9999)  # noqa: E501

    # Add a new instance of binance
    binance_2 = create_test_binance(
        database=db,
        msg_aggregator=rotki.msg_aggregator,
        name='binance_2',
    )
    exchanges = rotki.exchange_manager.connected_exchanges
    exchanges[Location.BINANCE].append(binance_2)
    # also add credentials in the DB
    db.add_exchange(
        name=binance_2.name,
        location=Location.BINANCE,
        api_key=binance_2.api_key,
        api_secret=binance_2.secret,
    )

    check_saved_events_for_exchange(
        exchange_location=Location.BINANCE,
        db=rotki.data.db,
        should_exist=True,
        query_range_key='{exchange}_{type}',
    )
    check_saved_events_for_exchange(
        exchange_location=Location.POLONIEX,
        db=rotki.data.db,
        should_exist=True,
        query_range_key='{exchange}_{type}',
    )

    RotkiUpgradeManager(rotki).run_upgrades()
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=False)
    check_saved_events_for_exchange(Location.POLONIEX, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.KRAKEN, rotki.data.db, should_exist=False)

    assert rotki.data.db.get_settings().last_app_upgrade == 1

    # Now let's add trades and everything should be kept
    for exchange_location in [Location.BINANCE, Location.KRAKEN]:
        db.add_trades([Trade(
            timestamp=Timestamp(1),
            location=exchange_location,
            base_asset=A_BTC,
            quote_asset=A_ETH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(1)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_ETH,
            link='foo',
            notes='boo',
        )])
        db.update_used_query_range(name=f'{str(exchange_location)}_trades_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501
        db.update_used_query_range(name=f'{str(exchange_location)}_margins_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501
        db.update_used_query_range(name=f'{str(exchange_location)}_asset_movements_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501

    RotkiUpgradeManager(rotki).run_upgrades()
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.POLONIEX, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.KRAKEN, rotki.data.db, should_exist=True)
    assert rotki.data.db.get_settings().last_app_upgrade == 1
