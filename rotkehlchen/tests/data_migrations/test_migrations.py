import json
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
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.types import Location, SupportedBlockchain, TradeType


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
            trade_tuples = ((
                f'custom-trade-id-{exchange_location}',
                1,
                exchange_location.serialize_for_db(),
                A_BTC.identifier,
                A_ETH.identifier,
                TradeType.BUY.serialize_for_db(),
                str(ONE),
                str(ONE),
                str(FVal('0.1')),
                A_ETH.identifier,
                'foo',
                'boo',
            ),)
            query = """
                INSERT INTO trades(
                id,
                time,
                location,
                base_asset,
                quote_asset,
                type,
                amount,
                rate,
                fee,
                fee_currency,
                link,
                notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            db.write_tuples(write_cursor=cursor, tuple_type='trade', query=query, tuples=trade_tuples)  # noqa: E501
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

    def botched_migration(cursor, rotki) -> None:
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


@pytest.mark.parametrize('data_migration_version', [None])
@pytest.mark.parametrize('perform_migrations_at_unlock', [False])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('perform_nodes_insertion', [False])
def test_migration_4(rotkehlchen_api_server):
    """
    Test that the fourth data migration for rotki works. This migration adds the ethereum nodes
    that will be used as open nodes to the database.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=MIGRATION_LIST[3:],
    )
    # Manually insert the old rpc setting in the table
    with database.user_write() as cursor:
        cursor.execute(
            'INSERT INTO settings(name, value) VALUES ("eth_rpc_endpoint", "https://localhost:5222");',  # noqa: E501
        )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()
    dir_path = Path(__file__).resolve().parent.parent.parent
    with database.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT * from settings where name=?', ('eth_rpc_endpoint',),
        )
        assert cursor.fetchone() is None, 'Setting should have been deleted'

    with open(dir_path / 'data' / 'nodes.json', 'r') as f:
        nodes = json.loads(f.read())
        web3_nodes = database.get_web3_nodes(blockchain=SupportedBlockchain.ETHEREUM)
        assert len(web3_nodes) == len(nodes) + 1
        for node in nodes:
            for web3_node in web3_nodes:
                if web3_node.node_info.name == node['name']:
                    assert web3_node.node_info.endpoint == node['endpoint']
                    assert web3_node.active == node['active']
                    assert web3_node.node_info.owned == node['owned']
                    assert web3_node.weight == FVal(node['weight'])
                    continue
        assert len(web3_nodes) >= 5
        assert web3_nodes[5].node_info.owned is True
        assert web3_nodes[5].node_info.endpoint == 'https://localhost:5222'


@pytest.mark.parametrize('data_migration_version', [None])
@pytest.mark.parametrize('perform_migrations_at_unlock', [False])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('perform_nodes_insertion', [False])
def test_migration_4_no_own_endpoint(rotkehlchen_api_server):
    """
    Test that the fourth data migration for rotki works when there is no custom node
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=MIGRATION_LIST[3:],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()
    dir_path = Path(__file__).resolve().parent.parent.parent
    with database.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT * from settings where name=?', ('eth_rpc_endpoint',),
        )
        assert cursor.fetchone() is None, 'Setting should have been deleted'
    web3_nodes = database.get_web3_nodes(blockchain=SupportedBlockchain.ETHEREUM)
    with open(dir_path / 'data' / 'nodes.json', 'r') as f:
        nodes = json.loads(f.read())
        assert len(nodes) == len(web3_nodes)


@pytest.mark.parametrize('data_migration_version', [None])
@pytest.mark.parametrize('perform_migrations_at_unlock', [False])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('perform_nodes_insertion', [False])
def test_migration_5(rotkehlchen_api_server):
    """
    Test that the fith data migration for rotki works.
    - Create two fake icons and check that the file name was correctly updated
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=MIGRATION_LIST[4:],
    )
    # Create some fake icon files
    icons_path = rotki.icon_manager.icons_dir
    Path(icons_path, '_ceth_0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').touch()
    Path(icons_path, '_ceth_0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').touch()
    Path(icons_path, '_ceth_0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').touch()
    Path(icons_path, 'eip155%3A1%2Ferc20%3A0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').touch()  # noqa: E501
    # the two files + the custom assets folder
    assert len(list(rotki.icon_manager.icons_dir.iterdir())) == 5
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, '_ceth_0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').exists() is False  # noqa: E501
    assert Path(icons_path, '_ceth_0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').exists() is False  # noqa: E501
    assert Path(icons_path, '_ceth_0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').exists() is False  # noqa: E501
