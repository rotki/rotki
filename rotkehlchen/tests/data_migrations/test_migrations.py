import operator
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import patch

import pytest

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.data_migrations.constants import LAST_DATA_MIGRATION
from rotkehlchen.data_migrations.manager import (
    MIGRATION_LIST,
    DataMigrationManager,
    MigrationRecord,
)
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.icons import IconManager
from rotkehlchen.tests.utils.blockchain import setup_evm_addresses_activity_mock
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChecksumEvmAddress, Location, TradeType

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader


def _create_invalid_icon(icon_identifier: str, icons_dir: Path) -> Path:
    icon_filepath = icons_dir / f'{icon_identifier}_small.png'
    with open(icon_filepath, 'wb') as f:
        f.write(b'abcd')

    return icon_filepath


class MockDataForMigrations(NamedTuple):
    db: DBHandler


class MockRotkiForMigrations:

    def __init__(self, db) -> None:
        self.data = MockDataForMigrations(db=db)
        self.msg_aggregator = db.msg_aggregator


def assert_progress_message(msg, step_num, description, migration_version, migration_steps) -> None:  # noqa: E501
    assert msg['type'] == 'data_migration_status'
    assert msg['data']['start_version'] == migration_version
    assert msg['data']['target_version'] == LAST_DATA_MIGRATION
    migration = msg['data']['current_migration']
    assert migration['version'] == migration_version
    assert migration['total_steps'] == (migration_steps if step_num != 0 else 0)
    assert migration['current_step'] == step_num
    if description is not None:
        assert description in migration['description']
    else:
        assert migration['description'] is None


def assert_add_addresses_migration_ws_messages(
        websocket_connection: 'WebsocketReader',
        migration_version: int,
        migration_steps: int,
        chain_to_added_address: list[dict],
) -> None:
    """Asserts that all steps of a data migration that adds addresses are correctly applied
    by checking the websocket messages"""
    num_messages = migration_steps + 1  # +1 for the message for added address
    websocket_connection.wait_until_messages_num(num=num_messages, timeout=10)
    assert websocket_connection.messages_num() == num_messages

    for i in range(migration_steps):
        msg = websocket_connection.pop_message()
        if i == migration_steps:  # message for added address
            assert msg['type'] == 'evm_accounts_detection'
            assert sorted(msg['data'], key=operator.itemgetter('evm_chain', 'address')) == sorted(
                chain_to_added_address, key=operator.itemgetter('evm_chain', 'address'),
            )  # checks that the addresses have been added
        elif i == 0:  # new migration round message
            assert_progress_message(msg, i, None, migration_version, migration_steps)

        if migration_version == 10:
            if i == 1:
                assert_progress_message(msg, i, 'Fetching new spam assets info', migration_version, migration_steps)  # noqa: E501
            elif i == 2:
                assert_progress_message(msg, i, 'Ensuring polygon node consistency', migration_version, migration_steps)  # noqa: E501
            if 3 <= i <= 6:
                assert_progress_message(msg, i, 'EVM chain activity', migration_version, migration_steps)  # noqa: E501
            elif i == 7:
                assert_progress_message(msg, i, 'Potentially write migrated addresses to the DB', migration_version, migration_steps)  # noqa: E501

        elif migration_version == 11:
            if i == 1:
                assert_progress_message(msg, i, 'Fetching new spam assets and rpc data info', migration_version, migration_steps)  # noqa: E501
            elif i in (2, 3):
                assert_progress_message(msg, i, 'EVM chain activity', migration_version, migration_steps)  # noqa: E501
            elif i == 4:
                assert_progress_message(msg, i, 'Potentially write migrated addresses to the DB', migration_version, migration_steps)  # noqa: E501


@pytest.mark.parametrize('use_custom_database', ['data_migration_v0.db'])
@pytest.mark.parametrize('data_migration_version', [0])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('new_db_unlock_actions', [None])
def test_migration_1(database):
    """
    Test that the first data migration for rotki works. This migration removes information about
    some exchanges when there is more than one instance or if it is kraken.

    In the test we setup instances of the exchanges to trigger the updates and one exchange
    (POLONIEX) that shouldn't be affected.
    """
    rotki = MockRotkiForMigrations(database)
    for exchange_location in [Location.BINANCE, Location.KRAKEN, Location.POLONIEX]:
        check_saved_events_for_exchange(
            exchange_location=exchange_location,
            db=database,
            should_exist=True,
            queryrange_formatstr='{exchange}_{type}',
        )
        cursor = database.conn.cursor()
        result = cursor.execute(
            'SELECT COUNT(*) from used_query_ranges WHERE name="bittrex_trades"',
        )
        assert result.fetchone()[0] == 1

    # Migration shouldn't execute and information should stay in database
    with database.user_write() as write_cursor:
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
            database.write_tuples(write_cursor=write_cursor, tuple_type='trade', query=query, tuples=trade_tuples)  # noqa: E501
            database.update_used_query_range(write_cursor=write_cursor, name=f'{exchange_location!s}_trades_{exchange_location!s}', start_ts=0, end_ts=9999)  # noqa: E501
            database.update_used_query_range(write_cursor=write_cursor, name=f'{exchange_location!s}_margins_{exchange_location!s}', start_ts=0, end_ts=9999)  # noqa: E501
            database.update_used_query_range(write_cursor=write_cursor, name=f'{exchange_location!s}_asset_movements_{exchange_location!s}', start_ts=0, end_ts=9999)  # noqa: E501

    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[0]],
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
    with database.conn.read_ctx() as cursor:
        assert rotki.data.db.get_settings(cursor).last_data_migration == LAST_DATA_MIGRATION


@pytest.mark.parametrize('use_custom_database', ['data_migration_v0.db'])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('data_migration_version', [0])
@pytest.mark.parametrize('new_db_unlock_actions', [None])
def test_failed_migration(database):
    """Test that a failed migration does not update DB setting and logs error"""
    rotki = MockRotkiForMigrations(database)

    def botched_migration(rotki, progress_handler) -> None:
        raise ValueError('ngmi')

    botched_list = [MigrationRecord(version=1, function=botched_migration)]

    migrate_mock = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=botched_list,
    )

    # Ignore websocket messages with notifications about db upgrade version.
    # By default they will be treated as errors since we have no websocket connection set up.
    rotki.msg_aggregator.consume_errors()

    with migrate_mock:
        DataMigrationManager(rotki).maybe_migrate_data()

    with database.conn.read_ctx() as cursor:
        settings = database.get_settings(cursor)
    assert settings.last_data_migration == 0, 'no migration should have happened'
    errors = rotki.msg_aggregator.consume_errors()
    warnings = rotki.msg_aggregator.consume_warnings()
    assert len(warnings) == 0
    assert len(errors) == 1
    assert errors[0] == 'Failed to run soft data migration to version 1 due to ngmi'


@pytest.mark.parametrize('data_migration_version', [2])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_migration_3(database, data_dir, greenlet_manager):
    """
    Test that the third data migration for rotki works. This migration removes icons of assets
    that are not valid images and update the list of ignored assets.
    """
    rotki = MockRotkiForMigrations(database)
    icon_manager = IconManager(data_dir=data_dir, coingecko=None, greenlet_manager=greenlet_manager)  # noqa: E501
    rotki.icon_manager = icon_manager
    btc_iconpath = _create_invalid_icon(A_BTC.identifier, icon_manager.icons_dir)
    eth_iconpath = _create_invalid_icon(A_ETH.identifier, icon_manager.icons_dir)

    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[2]],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    assert btc_iconpath.is_file() is False
    assert eth_iconpath.is_file() is False


@pytest.mark.parametrize('data_migration_version', [4])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_migration_5(database, data_dir, greenlet_manager):
    """
    Test that the fifth data migration for rotki works.
    - Create two fake icons and check that the file name was correctly updated
    """
    rotki = MockRotkiForMigrations(database)
    icon_manager = IconManager(data_dir=data_dir, coingecko=None, greenlet_manager=greenlet_manager)  # noqa: E501
    rotki.icon_manager = icon_manager
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[3]],
    )
    # Create some fake icon files
    icons_path = icon_manager.icons_dir
    Path(icons_path, '_ceth_0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').touch()
    Path(icons_path, '_ceth_0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').touch()
    Path(icons_path, '_ceth_0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').touch()
    Path(icons_path, 'eip155%3A1%2Ferc20%3A0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').touch()  # noqa: E501
    # the two files + the custom assets folder
    assert len(list(icon_manager.icons_dir.iterdir())) == 5
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, '_ceth_0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').exists() is False  # noqa: E501
    assert Path(icons_path, '_ceth_0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').exists() is False  # noqa: E501
    assert Path(icons_path, '_ceth_0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').exists() is False  # noqa: E501


@pytest.mark.parametrize('data_migration_version', [9])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
@pytest.mark.parametrize('ethereum_accounts', [[make_evm_address(), make_evm_address(), make_evm_address(), make_evm_address()]])  # noqa: E501
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_migration_10(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        websocket_connection: 'WebsocketReader',
) -> None:
    """
    Test that accounts are properly duplicated from ethereum to optimism and avalanche
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[4]],
    )
    avalanche_addresses = [ethereum_accounts[1], ethereum_accounts[3]]
    optimism_addresses = [ethereum_accounts[2], ethereum_accounts[3]]
    polygon_pos_addresses = [ethereum_accounts[3]]
    arbitrum_one_addresses = [ethereum_accounts[3]]

    # insert a bad polygon etherscan name in the database. By mistake we published an error
    # in this name and could affect users
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # replace the packaged db polygon pos etherscan node for the bad one
        # propagated in the data repo
        write_cursor.execute('DELETE from default_rpc_nodes WHERE name="polygon pos etherscan"')
        write_cursor.execute(
            'INSERT OR IGNORE INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '  # noqa: E501
            'VALUES (?, ?, ?, ?, ?, ?)',
            ('polygon etherscan', '', 0, 1, '0.25', 'POLYGON_POS'),
        )
        assert write_cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE name="polygon etherscan"').fetchone()[0] == 1  # noqa: E501

    with ExitStack() as stack:
        setup_evm_addresses_activity_mock(
            stack=stack,
            chains_aggregator=rotki.chains_aggregator,
            eth_contract_addresses=[ethereum_accounts[0]],
            ethereum_addresses=[],
            avalanche_addresses=avalanche_addresses,
            optimism_addresses=optimism_addresses,
            polygon_pos_addresses=polygon_pos_addresses,
            arbitrum_one_addresses=arbitrum_one_addresses,
        )
        stack.enter_context(migration_patch)
        DataMigrationManager(rotki).maybe_migrate_data()

    with rotki.data.db.conn.read_ctx() as cursor:  # make sure DB is also written
        accounts = rotki.data.db.get_blockchain_accounts(cursor)

    assert set(accounts.eth) == set(ethereum_accounts)
    assert set(rotki.chains_aggregator.accounts.eth) == set(ethereum_accounts)
    assert set(accounts.avax) == set(avalanche_addresses)
    assert set(rotki.chains_aggregator.accounts.avax) == set(avalanche_addresses)
    assert set(accounts.optimism) == set(optimism_addresses)
    assert set(rotki.chains_aggregator.accounts.optimism) == set(optimism_addresses)
    assert set(accounts.polygon_pos) == set(polygon_pos_addresses)
    assert set(rotki.chains_aggregator.accounts.polygon_pos) == set(polygon_pos_addresses)
    assert set(accounts.arbitrum_one) == set(arbitrum_one_addresses)
    assert set(rotki.chains_aggregator.accounts.arbitrum_one) == set(arbitrum_one_addresses)

    migration_steps = 8  # 4 (eth accounts) + 4 (potentially write to db + updating spam assets + polygon rpc + step 0)  # noqa: E501
    chain_to_added_address = [
        {'evm_chain': 'avalanche', 'address': ethereum_accounts[1]},
        {'evm_chain': 'avalanche', 'address': ethereum_accounts[3]},
        {'evm_chain': 'polygon_pos', 'address': ethereum_accounts[3]},
        {'evm_chain': 'optimism', 'address': ethereum_accounts[2]},
        {'evm_chain': 'optimism', 'address': ethereum_accounts[3]},
        {'evm_chain': 'arbitrum_one', 'address': ethereum_accounts[3]},
    ]
    assert_add_addresses_migration_ws_messages(websocket_connection, 10, migration_steps, chain_to_added_address)  # noqa: E501

    with GlobalDBHandler().conn.write_ctx() as write_cursor:  # check the global db for the polygon etherscan node  # noqa: E501
        assert write_cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE name="polygon etherscan"').fetchone()[0] == 0  # noqa: E501
        assert write_cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE name="polygon pos etherscan"').fetchone()[0] == 1  # noqa: E501
    with rotki.data.db.user_write() as write_cursor:  # check the user db for the polygon etherscan node  # noqa: E501
        assert write_cursor.execute('SELECT COUNT(*) FROM rpc_nodes WHERE name="polygon etherscan"').fetchone()[0] == 0  # noqa: E501
        assert write_cursor.execute('SELECT COUNT(*) FROM rpc_nodes WHERE name="polygon pos etherscan"').fetchone()[0] == 1  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('data_migration_version', [10])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # mainnet contract
    '0x280fc92644Dd4b9f5Bb5be652B4849611e8AC9Dd',  # mainnet + arbitrum activity only (test time)
]])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('network_mocking', [False])
def test_migration_11(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        websocket_connection: 'WebsocketReader',
) -> None:
    """
    Test migration 11.

    - Test that detecting arbitrum one accounts works properly
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # set high version so that DB data updates dont't get applied
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
            [
                (UpdateType.SPAM_ASSETS.serialize(), 999),
                (UpdateType.RPC_NODES.serialize(), 999),
                (UpdateType.CONTRACTS.serialize(), 999),
                (UpdateType.GLOBAL_ADDRESSBOOK.serialize(), 999),
            ],
        )
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[5]],
    )

    arbitrum_one_addresses = [ethereum_accounts[1]]
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    # check that detecting arbitrum one accounts works properly
    with rotki.data.db.conn.read_ctx() as cursor:  # make sure DB is also written
        accounts = rotki.data.db.get_blockchain_accounts(cursor)

    assert set(accounts.eth) == set(ethereum_accounts)
    assert set(rotki.chains_aggregator.accounts.eth) == set(ethereum_accounts)
    assert set(accounts.arbitrum_one) == set(arbitrum_one_addresses)
    assert set(rotki.chains_aggregator.accounts.arbitrum_one) == set(arbitrum_one_addresses)

    migration_steps = 5  # 2 (eth accounts) + 3 (potentially write to db + updating spam assets and rpc nodes + step 0)  # noqa: E501
    chain_to_added_address = [{'evm_chain': 'arbitrum_one', 'address': ethereum_accounts[1]}]
    assert_add_addresses_migration_ws_messages(websocket_connection, 11, migration_steps, chain_to_added_address)  # noqa: E501


@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
# make sure fixtures does not modify DB last_data_migration
@pytest.mark.parametrize('data_migration_version', [None])
def test_new_db_remembers_last_migration_even_if_no_migrations_run(database):
    """Test that a newly created database remembers the current last data migration
    at the time of creation even if no migration has actually ran"""
    rotki = MockRotkiForMigrations(database)
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM settings WHERE name="last_data_migration"')
        assert cursor.fetchone() is None

    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM settings WHERE name="last_data_migration"')
        assert int(cursor.fetchone()[0]) == LAST_DATA_MIGRATION
