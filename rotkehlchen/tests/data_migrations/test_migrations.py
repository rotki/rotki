import pytest

from rotkehlchen.constants.assets import A_ETH, A_BTC
from rotkehlchen.data_migrations.manager import DataMigrationManager
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.typing import (
    Location,
    AssetAmount,
    Fee,
    Price,
    Timestamp,
    TradeType,
)


@pytest.mark.parametrize('use_custom_database', ['data_migration_v0.db'])
@pytest.mark.parametrize('data_migration_version', [0])
def test_migration_1(
    use_custom_database,  # pylint: disable=unused-argument
    user_data_dir,  # pylint: disable=unused-argument
    rotkehlchen_api_server,
    added_exchanges,  # pylint: disable=unused-argument
    data_migration_version,  # pylint: disable=unused-argument
):
    """
    Test that the first data migration for rotki works. This migration removes information about
    some exchanges when there is more than one instance or if it is kraken.

    In the test we setup instances of the exchanges to trigger the updates and one exchange
    (POLONIEX) that shouldn't be affected.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    check_saved_events_for_exchange(
        exchange_location=Location.BINANCE,
        db=rotki.data.db,
        should_exist=True,
        queryrange_formatstr='{exchange}_{type}',
    )
    check_saved_events_for_exchange(
        exchange_location=Location.POLONIEX,
        db=rotki.data.db,
        should_exist=True,
        queryrange_formatstr='{exchange}_{type}',
    )

    DataMigrationManager(rotki).maybe_migrate_data()
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=False)
    check_saved_events_for_exchange(Location.POLONIEX, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.KRAKEN, rotki.data.db, should_exist=False)

    assert rotki.data.db.get_settings().last_data_migration == 1

    # Migration shouldn't execute and informatation should stay in database
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

    DataMigrationManager(rotki).maybe_migrate_data()
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.POLONIEX, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.KRAKEN, rotki.data.db, should_exist=True)
    assert rotki.data.db.get_settings().last_data_migration == 1
