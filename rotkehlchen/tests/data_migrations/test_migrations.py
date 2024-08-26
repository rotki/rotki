import operator
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.scroll.constants import SCROLL_ETHERSCAN_NODE
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_PAX, A_USDT
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.data_migrations.constants import LAST_DATA_MIGRATION
from rotkehlchen.data_migrations.manager import (
    MIGRATION_LIST,
    DataMigrationManager,
    MigrationRecord,
)
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.icons import IconManager
from rotkehlchen.tests.utils.blockchain import setup_evm_addresses_activity_mock
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    Location,
    SupportedBlockchain,
    TimestampMS,
    TradeType,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.inquirer import Inquirer
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader


def _create_invalid_icon(icon_identifier: str, icons_dir: Path) -> Path:
    icon_filepath = Path(icons_dir / f'{icon_identifier}_small.png')
    icon_filepath.write_bytes(b'abcd')
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

    for i in range(num_messages):
        msg = websocket_connection.pop_message()
        if i == migration_steps:  # message for added address. The message is only one and not one per chain. The added addresses per chain are checked from the message data  # noqa: E501
            assert msg['type'] == 'evmlike_accounts_detection'
            assert sorted(msg['data'], key=operator.itemgetter('chain', 'address')) == sorted(
                chain_to_added_address, key=operator.itemgetter('chain', 'address'),
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

        elif migration_version in {11, 12}:
            if i == 1:
                assert_progress_message(msg, i, 'Fetching new spam assets and rpc data info', migration_version, migration_steps)  # noqa: E501
            elif i in {2, 3}:
                assert_progress_message(msg, i, 'EVM chain activity', migration_version, migration_steps)  # noqa: E501
            elif i == 4:
                assert_progress_message(msg, i, 'Potentially write migrated addresses to the DB', migration_version, migration_steps)  # noqa: E501


def detect_accounts_migration_check(
        expected_detected_addresses_per_chain: dict[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, list[ChecksumEvmAddress]],  # noqa: E501
        migration_version: int,
        migration_steps: int,
        migration_list: list[MigrationRecord],
        current_evm_accounts: list[ChecksumEvmAddress],
        rotkehlchen_api_server: 'APIServer',
        websocket_connection: 'WebsocketReader',
) -> None:
    """Tests that a migration that detects accounts with activity in the given evm chains is
    properly applied."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # set high version so that DB data updates don't get applied
    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
            [
                (UpdateType.SPAM_ASSETS.serialize(), 999),
                (UpdateType.RPC_NODES.serialize(), 999),
                (UpdateType.CONTRACTS.serialize(), 999),
                (UpdateType.GLOBAL_ADDRESSBOOK.serialize(), 999),
                (UpdateType.ACCOUNTING_RULES.serialize(), 999),
            ],
        )
    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=migration_list,
    )

    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    # check that detecting chain accounts works properly
    with rotki.data.db.conn.read_ctx() as cursor:  # make sure DB is also written
        accounts = rotki.data.db.get_blockchain_accounts(cursor)

    assert set(accounts.eth) == set(current_evm_accounts)
    assert set(rotki.chains_aggregator.accounts.eth) == set(current_evm_accounts)
    chain_to_added_address = []
    for chain, chain_addresses in expected_detected_addresses_per_chain.items():
        assert set(getattr(accounts, chain.get_key())) == set(chain_addresses)
        assert set(getattr(rotki.chains_aggregator.accounts, chain.get_key())) == set(chain_addresses)  # noqa: E501
        chain_to_added_address.extend(
            [{'chain': chain.serialize(), 'address': address} for address in chain_addresses],
        )

    assert_add_addresses_migration_ws_messages(websocket_connection, migration_version, migration_steps, chain_to_added_address)  # noqa: E501


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
        last_data_migration = database.get_setting(cursor=cursor, name='last_data_migration')
    assert last_data_migration == 0, 'no migration should have happened'
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
    assert len(list(icon_manager.icons_dir.iterdir())) == 4
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, 'eip155%3A1%2Ferc20%3A0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').is_file() is True  # noqa: E501
    assert Path(icons_path, '_ceth_0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490_small.png').exists() is False  # noqa: E501
    assert Path(icons_path, '_ceth_0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D_small.png').exists() is False  # noqa: E501
    assert Path(icons_path, '_ceth_0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9_small.png').exists() is False  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE name="polygon etherscan"').fetchone()[0] == 1  # noqa: E501

    avalanche_addresses = [ethereum_accounts[1], ethereum_accounts[3]]
    optimism_addresses = [ethereum_accounts[2], ethereum_accounts[3]]
    polygon_pos_addresses = [ethereum_accounts[3]]
    with ExitStack() as stack:
        setup_evm_addresses_activity_mock(
            stack=stack,
            chains_aggregator=rotki.chains_aggregator,
            eth_contract_addresses=[ethereum_accounts[0]],
            ethereum_addresses=[],
            avalanche_addresses=avalanche_addresses,
            optimism_addresses=optimism_addresses,
            polygon_pos_addresses=polygon_pos_addresses,
        )
        detect_accounts_migration_check(
            expected_detected_addresses_per_chain={
                SupportedBlockchain.AVALANCHE: avalanche_addresses,
                SupportedBlockchain.OPTIMISM: optimism_addresses,
                SupportedBlockchain.POLYGON_POS: polygon_pos_addresses,
            },
            migration_version=10,
            migration_steps=8,  # 4 (current eth accounts) + 4 (potentially write to db + updating spam assets + polygon rpc + new round msg)  # noqa: E501
            migration_list=[MIGRATION_LIST[4]],
            current_evm_accounts=ethereum_accounts,
            rotkehlchen_api_server=rotkehlchen_api_server,
            websocket_connection=websocket_connection,
        )

    with GlobalDBHandler().conn.read_ctx() as cursor:  # check the global db for the polygon etherscan node  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE name="polygon etherscan"').fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes WHERE name="polygon pos etherscan"').fetchone()[0] == 1  # noqa: E501
    with rotki.data.db.conn.read_ctx() as cursor:  # check the user db for the polygon etherscan node  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM rpc_nodes WHERE name="polygon etherscan"').fetchone()[0] == 0  # noqa: E501
        assert cursor.execute('SELECT COUNT(*) FROM rpc_nodes WHERE name="polygon pos etherscan"').fetchone()[0] == 1  # noqa: E501


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
    detect_accounts_migration_check(
        expected_detected_addresses_per_chain={SupportedBlockchain.ARBITRUM_ONE: [ethereum_accounts[1]]},  # noqa: E501
        migration_version=11,
        migration_steps=5,  # 2 (current eth accounts) + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
        migration_list=[MIGRATION_LIST[5]],
        current_evm_accounts=ethereum_accounts,
        rotkehlchen_api_server=rotkehlchen_api_server,
        websocket_connection=websocket_connection,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('data_migration_version', [12])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',  # mainnet contract
    '0x78C13393Aee675DD7ED07ce992210750D1F5dB88',  # mainnet + gnosis + base + other evm chains activity  # noqa: E501
]])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('network_mocking', [False])
def test_migration_13(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        websocket_connection: 'WebsocketReader',
) -> None:
    """
    Test migration 13

    - Test that detecting gnosis and base accounts works properly
    """
    detect_accounts_migration_check(
        expected_detected_addresses_per_chain={
            SupportedBlockchain.GNOSIS: [ethereum_accounts[1]],
            SupportedBlockchain.BASE: [ethereum_accounts[1]],
        },
        migration_version=13,
        migration_steps=5,  # 2 (current eth accounts) + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
        migration_list=[MIGRATION_LIST[6]],
        current_evm_accounts=ethereum_accounts,
        rotkehlchen_api_server=rotkehlchen_api_server,
        websocket_connection=websocket_connection,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('data_migration_version', [13])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',  # should have zksynclite
    '0xfa8666aE51F5b136596248d9411b03AC9040fff0',  # should have scroll
    '0x2F4c0f60f2116899FA6D4b9d8B979167CE963d25',  # should have neither
]])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('scroll_manager_connect_at_start', [(SCROLL_ETHERSCAN_NODE,)])
def test_migration_14(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        websocket_connection: 'WebsocketReader',
) -> None:
    """
    Test migration 14

    - Test that detecting scroll and zksynclite accounts works properly
    """
    detect_accounts_migration_check(
        expected_detected_addresses_per_chain={
            SupportedBlockchain.SCROLL: [ethereum_accounts[1]],
            SupportedBlockchain.ZKSYNC_LITE: [ethereum_accounts[0]],
        },
        migration_version=14,
        migration_steps=6,  # 3 (current eth accounts) + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
        migration_list=[MIGRATION_LIST[7]],
        current_evm_accounts=ethereum_accounts,
        rotkehlchen_api_server=rotkehlchen_api_server,
        websocket_connection=websocket_connection,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('data_migration_version', [14])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('base_accounts', [[
    '0xAE70bC0Cbe03ceF2a14eCA507a2863441C6Df7A1',
    '0xC960338B529e0353F570f62093Fd362B8FB55f0B',
]])
def test_migration_15(rotkehlchen_api_server: 'APIServer', inquirer: 'Inquirer') -> None:
    """Test migration 15

    - Test that Hop LP tokens' protocol is set after the migration."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    base_manager = rotki.chains_aggregator.get_chain_manager(SupportedBlockchain.BASE)
    inquirer.inject_evm_managers([(ChainID.BASE, base_manager)])

    # check Hop LP token price before migration
    test_hop_lp_1 = get_or_create_evm_token(
        userdb=rotki.data.db,
        evm_address=string_to_evm_address('0xbBA837dFFB3eCf4638D200F11B8c691eA641AdCb'),
        chain_id=ChainID.ARBITRUM_ONE,
        token_kind=EvmTokenKind.ERC20,
    )
    test_hop_lp_2 = get_or_create_evm_token(
        userdb=rotki.data.db,
        evm_address=string_to_evm_address('0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D'),
        chain_id=ChainID.BASE,
        token_kind=EvmTokenKind.ERC20,
    )
    assert test_hop_lp_2.protocol is None
    assert inquirer.find_usd_price(test_hop_lp_2) == ZERO_PRICE

    with rotki.data.db.conn.write_ctx() as write_cursor:
        DBHistoryEvents(rotki.data.db).add_history_events(
            write_cursor=write_cursor,
            history=[
                EvmEvent(
                    sequence_index=2,
                    timestamp=TimestampMS(1714582939000),
                    location=Location.ARBITRUM_ONE,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                    asset=test_hop_lp_1,
                    balance=Balance(amount=FVal('0.023220146656543904')),
                    location_label='0xC960338B529e0353F570f62093Fd362B8FB55f0B',
                    notes='Receive 0.023220146656543904 HOP-LP-rETH after providing liquidity in Hop',  # noqa: E501
                    tx_hash=deserialize_evm_tx_hash('0x2ab0135c1c200cf5095bd107c9e8c0d712b2a14374cc328848256d896d6e4685'),
                    counterparty=CPT_HOP,
                    address=ZERO_ADDRESS,
                ),
                EvmEvent(
                    sequence_index=2,
                    timestamp=TimestampMS(1714582939000),
                    location=Location.BASE,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                    asset=test_hop_lp_2,
                    balance=Balance(amount=FVal('0.023220146656543904')),
                    location_label='0xAE70bC0Cbe03ceF2a14eCA507a2863441C6Df7A1',
                    notes='Receive 0.023220146656543904 HOP-LP-ETH after providing liquidity in Hop',  # noqa: E501
                    tx_hash=deserialize_evm_tx_hash('0xa50286f6288ca13452a490d766aaf969d20cce7035b514423a7b1432fd329cc5'),
                    counterparty=CPT_HOP,
                    address=ZERO_ADDRESS,
                ),
            ],
        )
    with patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[8]],
    ):
        DataMigrationManager(rotki).maybe_migrate_data()

    # Hop LP token price before migration
    assert inquirer.find_usd_price(test_hop_lp_2).is_close(3803.566408)


@pytest.mark.parametrize('data_migration_version', [15])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
def test_migration_16(rotkehlchen_api_server: 'APIServer', globaldb: 'GlobalDBHandler') -> None:
    """Test migration 16

    - Test that all underlying tokens that are their own parent are removed."""
    # add some underlying tokens with their own parent as themselves
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO underlying_tokens_list (identifier, parent_token_entry, weight) VALUES (?, ?, ?)',  # noqa: E501
            (A_USDT.identifier, A_USDT.identifier, 1),
        )
        write_cursor.execute(
            'INSERT INTO underlying_tokens_list (identifier, parent_token_entry, weight) VALUES (?, ?, ?)',  # noqa: E501
            (A_PAX.identifier, A_PAX.identifier, 1),
        )

    with globaldb.conn.read_ctx() as cursor:
        underlying_count_before = cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list',
        ).fetchone()[0]
        assert cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE identifier=parent_token_entry',
        ).fetchone()[0] == 2

    with patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[9]],
    ):
        DataMigrationManager(rotkehlchen_api_server.rest_api.rotkehlchen).maybe_migrate_data()

    # Check that the two underlying tokens have been removed
    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list',
        ).fetchone()[0] == underlying_count_before - 2
        assert cursor.execute(
            'SELECT COUNT(*) FROM underlying_tokens_list WHERE identifier=parent_token_entry',
        ).fetchone()[0] == 0


@pytest.mark.parametrize('data_migration_version', [16])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
def test_migration_17(rotkehlchen_api_server: 'APIServer', globaldb: 'GlobalDBHandler') -> None:
    """Test migration 17

    - Test that address that appear more than once get de-duplicated and all
    of them get the new "special" value for blockchain
    """
    bad_address, tether_address = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'  # noqa: E501
    inserted_rows = [
        (bad_address, 'yabir.eth', None),
        (bad_address, 'yabirgb.eth', None),
        (tether_address, 'Black Tether', None),
    ]

    for conn in (
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn,
        globaldb.conn,
    ):
        with conn.write_ctx() as write_cursor:
            write_cursor.executemany(
                'INSERT INTO address_book (address, name, blockchain) VALUES (?, ?, ?)',
                inserted_rows,
            )

    with patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[10]],
    ):
        DataMigrationManager(rotkehlchen_api_server.rest_api.rotkehlchen).maybe_migrate_data()

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT * FROM address_book WHERE address IN (?, ?)',
            (bad_address, tether_address),
        ).fetchall() == [
            (tether_address, ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, 'Black Tether'),
            (bad_address, ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, 'yabirgb.eth'),
        ]


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


def test_last_data_migration_constant() -> None:
    """Test that the LAST_DATA_MIGRATION constant is updated correctly"""
    assert max(x.version for x in MIGRATION_LIST) == LAST_DATA_MIGRATION
