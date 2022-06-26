from pathlib import Path
from unittest.mock import patch

import pytest

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.data_migrations.manager import (
    MIGRATION_LIST,
    DataMigrationManager,
    MigrationRecord,
)
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.types import AssetAmount, Fee, Location, Price, Timestamp, TradeType


def _create_invalid_icon(icon_identifier: str, icons_dir: Path) -> Path:
    icon_filepath = icons_dir / f'{icon_identifier}_small.png'
    with open(icon_filepath, 'wb') as f:
        f.write(b'abcd')

    return icon_filepath


@pytest.mark.parametrize('use_custom_database', ['data_migration_v0.db'])
@pytest.mark.parametrize('data_migration_version', [None])
@pytest.mark.parametrize('perform_migrations_at_unlock', [False])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
def test_migration_1(rotkehlchen_api_server):
    """
    Test that the first data migration for rotki works. This migration removes information about
    some exchanges when there is more than one instance or if it is kraken.

    In the test we setup instances of the exchanges to trigger the updates and one exchange
    (POLONIEX) that shouldn't be affected.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    for exchange_location in [Location.BINANCE, Location.KRAKEN, Location.POLONIEX]:
        check_saved_events_for_exchange(
            exchange_location=exchange_location,
            db=rotki.data.db,
            should_exist=True,
            queryrange_formatstr='{exchange}_{type}',
        )
        cursor = db.conn.cursor()
        result = cursor.execute(
            'SELECT COUNT(*) from used_query_ranges WHERE name="bittrex_trades"',
        )
        assert result.fetchone()[0] == 1

    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=MIGRATION_LIST[:1],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()
    errors = rotki.msg_aggregator.consume_errors()
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=False)
    check_saved_events_for_exchange(Location.POLONIEX, rotki.data.db, should_exist=True)
    check_saved_events_for_exchange(Location.KRAKEN, rotki.data.db, should_exist=False)
    cursor = db.conn.cursor()
    result = cursor.execute(
        'SELECT COUNT(*) from used_query_ranges WHERE name="bittrex_trades"',
    )
    assert result.fetchone()[0] == 0
    assert rotki.data.db.get_settings(cursor).last_data_migration == 1

    # Migration shouldn't execute and information should stay in database
    with db.user_write() as cursor:
        for exchange_location in [Location.BINANCE, Location.KRAKEN]:
            db.add_trades(
                write_cursor=cursor,
                trades=[
                    Trade(
                        timestamp=Timestamp(1),
                        location=exchange_location,
                        base_asset=A_BTC,
                        quote_asset=A_ETH,
                        trade_type=TradeType.BUY,
                        amount=AssetAmount(ONE),
                        rate=Price(ONE),
                        fee=Fee(FVal('0.1')),
                        fee_currency=A_ETH,
                        link='foo',
                        notes='boo',
                    )])
            db.update_used_query_range(write_cursor=cursor, name=f'{str(exchange_location)}_trades_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501
            db.update_used_query_range(write_cursor=cursor, name=f'{str(exchange_location)}_margins_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501
            db.update_used_query_range(write_cursor=cursor, name=f'{str(exchange_location)}_asset_movements_{str(exchange_location)}', start_ts=0, end_ts=9999)  # noqa: E501

        with migration_patch:
            DataMigrationManager(rotki).maybe_migrate_data()
        errors = rotki.msg_aggregator.consume_errors()
        warnings = rotki.msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        check_saved_events_for_exchange(Location.BINANCE, rotki.data.db, should_exist=True)
        check_saved_events_for_exchange(Location.POLONIEX, rotki.data.db, should_exist=True)
        check_saved_events_for_exchange(Location.KRAKEN, rotki.data.db, should_exist=True)
        assert rotki.data.db.get_settings(cursor).last_data_migration == 1


@pytest.mark.parametrize('use_custom_database', ['data_migration_v0.db'])
@pytest.mark.parametrize('data_migration_version', [None])
@pytest.mark.parametrize('perform_migrations_at_unlock', [False])
def test_failed_migration(rotkehlchen_api_server):
    """Test that a failed migration does not update DB setting and logs error"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db

    def botched_migration(rotki) -> None:
        raise ValueError('ngmi')

    botched_list = [MigrationRecord(version=1, function=botched_migration)]

    migrate_mock = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=botched_list,
    )
    with migrate_mock:
        DataMigrationManager(rotki).maybe_migrate_data()

    with db.conn.read_ctx() as cursor:
        settings = db.get_settings(cursor)
    assert settings.last_data_migration == 0, 'no upgrade should have happened'
    errors = rotki.msg_aggregator.consume_errors()
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    assert len(errors) == 1
    assert errors[0] == 'Failed to run soft data migration to version 1 due to ngmi'


@pytest.mark.parametrize('data_migration_version', [None])
@pytest.mark.parametrize('perform_migrations_at_unlock', [False])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_migration_3(rotkehlchen_api_server):
    """
    Test that the third data migration for rotki works. This migration removes icons of assets
    that are not valid images and update the list of ignored assets using cryptoscamdb.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    icon_manager = rotki.icon_manager

    btc_iconpath = _create_invalid_icon(A_BTC.identifier, icon_manager.icons_dir)
    eth_iconpath = _create_invalid_icon(A_ETH.identifier, icon_manager.icons_dir)

    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=MIGRATION_LIST[2:],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    assert btc_iconpath.is_file() is False
    assert eth_iconpath.is_file() is False
