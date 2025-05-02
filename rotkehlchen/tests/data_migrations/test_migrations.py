import json
import operator
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple
from unittest.mock import _patch, patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.constants import APPDIR_NAME, ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.data_migrations.constants import LAST_DATA_MIGRATION
from rotkehlchen.data_migrations.manager import (
    MIGRATION_LIST,
    DataMigrationManager,
    MigrationRecord,
)
from rotkehlchen.db.constants import UpdateType
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_delete_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.icons import IconManager
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.blockchain import setup_evm_addresses_activity_mock
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    CacheType,
    ChecksumEvmAddress,
    Location,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.greenlets.manager import GreenletManager
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader


def _create_invalid_icon(icon_identifier: str, icons_dir: Path) -> Path:
    icon_filepath = Path(icons_dir / f'{icon_identifier}_small.png')
    icon_filepath.write_bytes(b'abcd')
    return icon_filepath


class MockDataForMigrations(NamedTuple):
    db: DBHandler


class MockRotkiForMigrations(Rotkehlchen):

    def __init__(self, db: DBHandler) -> None:  # pylint: disable=W0231 # inheritance from Rotkehlchen is just for the type checker
        self.data = MockDataForMigrations(db=db)  # type: ignore
        self.msg_aggregator = db.msg_aggregator


def assert_progress_message(msg: dict[str, Any], step_num: int, description: str | None, migration_version: int, migration_steps: int) -> None:  # noqa: E501
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
                assert_progress_message(msg, i, 'Ensuring polygon node consistency', migration_version, migration_steps)  # noqa: E501
            elif i == 2:
                assert_progress_message(msg, i, 'Fetching new spam assets and rpc data info', migration_version, migration_steps)  # noqa: E501
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
        migration_manager = DataMigrationManager(rotki)
        migration_manager.maybe_migrate_data()
        assert migration_manager.progress_handler.current_round_total_steps == migration_manager.progress_handler.current_round_current_step + 1  # noqa: E501

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
def test_migration_1(database: DBHandler) -> None:
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
            "SELECT COUNT(*) from used_query_ranges WHERE name='bittrex_trades'",
        )
        assert result.fetchone()[0] == 1

    # Migration shouldn't execute and information should stay in database
    with database.user_write() as write_cursor:
        for exchange_location in [Location.BINANCE, Location.KRAKEN]:
            margin_tuples = ((
                 f'custom-margin-id-{exchange_location}',  # id
                 exchange_location.serialize_for_db(),  # location
                 1,  # open_time
                 2,  # close_time
                 str(ONE),  # profit_loss
                 A_BTC.identifier,  # pl_currency
                 str(FVal('0.1')),  # fee
                 A_ETH.identifier,  # fee_currency
                 'foo',  # link
                 'boo',  # notes
             ),)

            query = """
            INSERT INTO margin_positions(
                id,
                location,
                open_time,
                close_time,
                profit_loss,
                pl_currency,
                fee,
                fee_currency,
                link,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            database.write_tuples(write_cursor=write_cursor, tuple_type='margin_position', query=query, tuples=margin_tuples)  # noqa: E501
            database.update_used_query_range(write_cursor=write_cursor, name=f'{exchange_location!s}_margins_{exchange_location!s}', start_ts=Timestamp(0), end_ts=Timestamp(9999))  # noqa: E501

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
def test_failed_migration(database: DBHandler) -> None:
    """Test that a failed migration does not update DB setting and logs error"""
    rotki = MockRotkiForMigrations(database)

    def botched_migration(rotki: MockDataForMigrations, progress_handler: 'MigrationProgressHandler') -> None:  # noqa: E501
        raise ValueError('ngmi')

    botched_list = [MigrationRecord(version=1, function=botched_migration)]  # type: ignore

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
def test_migration_3(
        database: DBHandler,
        data_dir: Path,
        greenlet_manager: 'GreenletManager',
) -> None:
    """
    Test that the third data migration for rotki works. This migration removes icons of assets
    that are not valid images and update the list of ignored assets.
    """
    rotki = MockRotkiForMigrations(database)
    icon_manager = IconManager(data_dir=data_dir, coingecko=Coingecko(None), greenlet_manager=greenlet_manager)  # noqa: E501
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
def test_migration_5(
        database: DBHandler,
        data_dir: Path,
        greenlet_manager: 'GreenletManager',
) -> None:
    """
    Test that the fifth data migration for rotki works.
    - Create two fake icons and check that the file name was correctly updated
    """
    rotki = MockRotkiForMigrations(database)
    icon_manager = IconManager(data_dir=data_dir, coingecko=Coingecko(None), greenlet_manager=greenlet_manager)  # noqa: E501
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


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['github_branch_matcher'])
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
        write_cursor.execute("DELETE from default_rpc_nodes WHERE name='polygon pos etherscan'")
        write_cursor.execute(
            'INSERT OR IGNORE INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '  # noqa: E501
            'VALUES (?, ?, ?, ?, ?, ?)',
            ('polygon etherscan', '', 0, 1, '0.25', 'POLYGON_POS'),
        )
        assert write_cursor.execute("SELECT COUNT(*) FROM default_rpc_nodes WHERE name='polygon etherscan'").fetchone()[0] == 1  # noqa: E501

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
        assert cursor.execute("SELECT COUNT(*) FROM default_rpc_nodes WHERE name='polygon etherscan'").fetchone()[0] == 0  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM default_rpc_nodes WHERE name='polygon pos etherscan'").fetchone()[0] == 1  # noqa: E501
    with rotki.data.db.conn.read_ctx() as cursor:  # check the user db for the polygon etherscan node  # noqa: E501
        assert cursor.execute("SELECT COUNT(*) FROM rpc_nodes WHERE name='polygon etherscan'").fetchone()[0] == 0  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['github_branch_matcher'])
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
        expected_detected_addresses_per_chain={SupportedBlockchain.ARBITRUM_ONE: ethereum_accounts},  # noqa: E501
        migration_version=11,
        migration_steps=5,  # 2 (current eth accounts) + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
        migration_list=[MIGRATION_LIST[5]],
        current_evm_accounts=ethereum_accounts,
        rotkehlchen_api_server=rotkehlchen_api_server,
        websocket_connection=websocket_connection,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['github_branch_matcher'])
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
            SupportedBlockchain.GNOSIS: ethereum_accounts,
            SupportedBlockchain.BASE: ethereum_accounts,
        },
        migration_version=13,
        migration_steps=5,  # 2 (current eth accounts) + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
        migration_list=[MIGRATION_LIST[6]],
        current_evm_accounts=ethereum_accounts,
        rotkehlchen_api_server=rotkehlchen_api_server,
        websocket_connection=websocket_connection,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['github_branch_matcher'])
@pytest.mark.parametrize('data_migration_version', [13])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',  # should have zksynclite
    '0xfa8666aE51F5b136596248d9411b03AC9040fff0',  # should have scroll
    '0xDeeF02aDA5b089f851F2a1C0301D46631514D312',  # should have neither
]])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('network_mocking', [False])
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
@pytest.mark.parametrize('data_migration_version', [17])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
def test_migration_18(rotkehlchen_api_server: 'APIServer') -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    ethereum_manager = rotki.chains_aggregator.ethereum
    related_address1, related_address2, other_address, yabireth = '0x9531C059098e3d194fF87FebB587aB07B30B1306', '0x8Fe178db26ebA2eEdb22575265bf10A63c395a3d', '0x3c89cd398aCcFCf0e046d325c4805A98723F8630', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # noqa: E501
    with rotki.data.db.user_write() as write_cursor:  # let's add 2 tracked accounts
        write_cursor.executemany(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES(?, ?)',
            [
                ('ETH', related_address1),
                ('ETH', related_address2),
                ('ETH', other_address),
                ('ETH', yabireth),
            ],
        )
        write_cursor.execute(  # put manualcurrent oracle in the DB to test its removal
            'INSERT INTO settings(name, value) VALUES(?, ?)',
            ('current_price_oracles', '["coingecko", "cryptocompare", "manualcurrent", "defillama"]'),  # noqa: E501
        )

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT value FROM unique_cache WHERE key=?', ('YEARN_VAULTS',),
        ).fetchone()[0] == '179'

    approval_1 = deserialize_evm_tx_hash('0xbb8280cc9ca9de1d33e573a4381d88525a214fc45f84415129face03125ba22f')  # noqa: E501
    approval_2 = deserialize_evm_tx_hash('0x5dbe2be40c2ee60b33c9b9b183fc3f1290352787540cbb2e87e131e6fb1a8865')  # noqa: E501
    vested_delegation_tol2 = deserialize_evm_tx_hash('0x48321bb00e5c5b67f080991864606dbc493051d20712735a579d7ae31eca3d78')  # noqa: E501
    normal_delegation_tol2 = deserialize_evm_tx_hash('0xed80711e4cb9c428790f0d9b51f79473bf5253d5d03c04d958d411e7fa34a92e')  # noqa: E501
    stake_withdrawn = deserialize_evm_tx_hash('0xfeeec3405306ef50108e2ac1221ef59124395306c8bf133abe24f6f993014020')  # noqa: E501
    stake_delegated = deserialize_evm_tx_hash('0xc49b141fcde5baa467f6cd0d574fcfe54077eda4a95dc061eccc833f247a89a6')  # noqa: E501
    stake_delegate_locked = deserialize_evm_tx_hash('0xf009486131b2875d2f57ccc35caa20d768f7e16f489a0d215a8e819741ee4acb')  # noqa: E501
    stake_delegate_vested = deserialize_evm_tx_hash('0x18c7fbaeb3159812acf823d8cd1ef3f6b9364548ca38aa58ca52c5c21d8f5e8c')  # noqa: E501
    kept_txs = [approval_1, approval_2, vested_delegation_tol2, normal_delegation_tol2, stake_withdrawn, stake_delegated, stake_delegate_locked, stake_delegate_vested]  # noqa: E501
    for tx_hash in kept_txs:  # transactions related to our addresses and thegraph
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_manager.node_inquirer,
            tx_hash=tx_hash,
        )

    # transaction that will be marked as spam
    spam_hash = deserialize_evm_tx_hash('0xfc8b1ea372fc7d82e6516dff022ea874c9323c8d5f2afe517aa588e1a4b1aab6')  # noqa: E501
    with rotki.data.db.conn.read_ctx() as cursor:
        spam_transaction, _ = ethereum_manager.transactions.get_or_create_transaction(
            cursor=cursor,
            tx_hash=spam_hash,
            relevant_address=string_to_evm_address(yabireth),
        )
        spam_transaction_id = spam_transaction.get_or_query_db_id(cursor)
        assert json.loads(cursor.execute(  # make sure manual oracle is there before the migration
            "SELECT value from settings where name='current_price_oracles'",
        ).fetchone()[0]) == ['coingecko', 'cryptocompare', 'manualcurrent', 'defillama']

    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(  # mark as spam but also count as decoded. Same as we were doing in 1.35.0  # noqa: E501
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES(?, ?)',
            [(spam_transaction_id, 0), (spam_transaction_id, 1)],  # decoded and spam
        )

    # mark a few assets as spam
    tokens = [
        EvmToken('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),  # new eure
        EvmToken('eip155:100/erc20:0x8E34bfEC4f6Eb781f9743D9b4af99CD23F9b7053'),  # new GBPe
        EvmToken('eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E'),  # legacy eure
        EvmToken('eip155:1/erc20:0x3231Cb76718CDeF2155FC47b5286d82e6eDA273f'),  # eure ethereum
    ]
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        for token in tokens:
            set_token_spam_protocol(write_cursor=write_cursor, token=token, is_spam=True)

            # remove the asset from the whitelist if it was there
            globaldb_delete_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(CacheType.SPAM_ASSET_FALSE_POSITIVE,),
                values=(token.identifier,),
            )
            AssetResolver.clean_memory_cache(token.identifier)

    # add to ignored assets if it wasn't there
    rotki.data.add_ignored_assets(assets=tokens)

    # add all the transactions that are irrelevant to us, emulating the problem
    # that all transactions of 0xF55041E37E12cD407ad00CE2910B8269B01263b9 were saved
    # in the DB
    bad_txs = [
        deserialize_evm_tx_hash('0x77ee18c542cc382b5a9d894a2a5561ca76d7c16ff7bea90353e77c2713e9a542'),
        deserialize_evm_tx_hash('0xd2e2c7d1e17c36ffeb4f41d870c661af53cb757d17fd739afc92de6464715a92'),
        deserialize_evm_tx_hash('0x36de0e0f45888a2aeb8677707dcc77799fb2b10a0a51e1d0af1b7c511a66637d'),
        deserialize_evm_tx_hash('0x997a1ec28f18066476a02f3f96422ac48da0056ae210e14b5c4cac5a71be600b'),
        deserialize_evm_tx_hash('0x83be133424a4d1dd6198c7f4b4c82b5983a90f70c7cc083e533823240cb3397b'),
        deserialize_evm_tx_hash('0x8c97c09994aba8f7b619a9d793a1c5fb58028ea1bb9b03ea9a48e76b0a4eac84'),
        deserialize_evm_tx_hash('0xf73312097128b62a6b3b82229f29a4d12bd4fff8587e8eb581a9a469a170b12d'),
        deserialize_evm_tx_hash('0x367be0c17e7b890fcbcba0c46b5bb7335ac00a8546960b6c818c184207b30c0b'),
    ]
    with rotki.data.db.conn.read_ctx() as cursor:
        for tx_hash in bad_txs:
            ethereum_manager.transactions.get_or_create_transaction(cursor=cursor, tx_hash=tx_hash, relevant_address=None)  # noqa:E501
            ethereum_manager.transactions.get_or_query_transaction_receipt(tx_hash=tx_hash)

    with rotki.data.db.conn.read_ctx() as cursor:
        assert {x[0] for x in cursor.execute('SELECT tx_hash FROM evm_transactions').fetchall()} == set(kept_txs + bad_txs + [spam_hash])  # make sure they are all written in the DB  # noqa: E501

        assert cursor.execute(  # make sure the given tokens were marked as ignored
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value IN (?, ?, ?, ?)",  # noqa: E501
            [token.identifier for token in tokens],
        ).fetchone()[0] == len(tokens)

        for token in tokens:  # ensure that they have been marked as spam
            assert GlobalDBHandler.get_protocol_for_asset(token.identifier) == SPAM_PROTOCOL

    with patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[8]],
    ):
        migration_manager = DataMigrationManager(rotkehlchen_api_server.rest_api.rotkehlchen)
        migration_manager.maybe_migrate_data()
        assert migration_manager.progress_handler.current_round_total_steps == migration_manager.progress_handler.current_round_current_step  # noqa: E501

    with rotki.data.db.conn.read_ctx() as cursor:
        result_kept_txs = {x[0] for x in cursor.execute('SELECT tx_hash FROM evm_transactions').fetchall()}  # noqa: E501
        assert cursor.execute(  # now make sure they are no longer ignored
            "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value IN (?, ?, ?, ?)",  # noqa: E501
            [token.identifier for token in tokens],
        ).fetchone()[0] == 0

        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=?',
            (spam_transaction_id,),
        ).fetchone()[0] == 0
        assert json.loads(cursor.execute(  # make sure manual oracle is gone after the migration
            "SELECT value from settings where name='current_price_oracles'",
        ).fetchone()[0]) == ['coingecko', 'cryptocompare', 'defillama']

    for token in tokens:
        assert GlobalDBHandler.get_protocol_for_asset(token.identifier) != SPAM_PROTOCOL

    assert result_kept_txs == set(kept_txs + [spam_hash])  # after the migration see all irrelevant transactions are deleted  # noqa: E501

    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT value FROM unique_cache WHERE key=?', ('YEARN_VAULTS',),
        ).fetchall() == []


@pytest.mark.parametrize('perform_upgrades_at_unlock', [False])
# make sure fixtures does not modify DB last_data_migration
@pytest.mark.parametrize('data_migration_version', [None])
def test_new_db_remembers_last_migration_even_if_no_migrations_run(database: DBHandler) -> None:
    """Test that a newly created database remembers the current last data migration
    at the time of creation even if no migration has actually ran"""
    rotki = MockRotkiForMigrations(database)
    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute("SELECT value FROM settings WHERE name='last_data_migration'")
        assert cursor.fetchone() is None

    migration_patch: _patch[list] = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    with rotki.data.db.conn.read_ctx() as cursor:
        cursor.execute("SELECT value FROM settings WHERE name='last_data_migration'")
        assert int(cursor.fetchone()[0]) == LAST_DATA_MIGRATION


def test_last_data_migration_constant() -> None:
    """Test that the LAST_DATA_MIGRATION constant is updated correctly"""
    assert max(x.version for x in MIGRATION_LIST) == LAST_DATA_MIGRATION


@pytest.mark.parametrize('data_migration_version', [18])
@pytest.mark.parametrize('perform_upgrades_at_unlock', [True])
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_migration_19(
        rotkehlchen_api_server: 'APIServer',
        gnosis_accounts: list[ChecksumEvmAddress],
) -> None:
    """
    Test migration 19

    - Test that wrongly created folders get deleted
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    with database.user_write() as write_cursor:
        database.update_used_query_range(
            write_cursor=write_cursor,
            name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{gnosis_accounts[0]}',
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
        )
        database.update_used_query_range(  # range for address not tracked
            write_cursor=write_cursor,
            name=f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{"0x805aF152eebc7e280628A0Bb30Dd916b5B7716fb"}',
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
        )
        database.update_used_query_range(  # different range name
            write_cursor=write_cursor,
            name=f'transactions_{gnosis_accounts[0]}',
            start_ts=Timestamp(0),
            end_ts=Timestamp(1),
        )

    bad_appdir_folder = rotki.data.db.user_data_dir / APPDIR_NAME
    bad_appdir_folder.mkdir()
    (bad_appdir_folder / 'myso.parquet').touch()

    migration_patch = patch(
        'rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[MIGRATION_LIST[9]],
    )
    with migration_patch:
        DataMigrationManager(rotki).maybe_migrate_data()

    assert not bad_appdir_folder.exists()

    with database.conn.read_ctx() as cursor:
        entries = {row[0] for row in cursor.execute('SELECT name FROM used_query_ranges')}

    assert entries == {
        f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{gnosis_accounts[0]}',
        f'transactions_{gnosis_accounts[0]}',
    }
