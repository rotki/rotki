import json
from contextlib import ExitStack
from typing import Callable, Optional
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.updates import RotkiDataUpdater, UpdateType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    AddressbookEntry,
    ChainID,
    EvmTokenKind,
    SupportedBlockchain,
)
from rotkehlchen.utils.version_check import VersionCheckResult

ETHEREUM_SPAM_ASSET_ADDRESS = make_evm_address()
OPTIMISM_SPAM_ASSET_ADDRESS = make_evm_address()

ADDRESSBOOK_ADDRESS_1 = make_evm_address()
ADDRESSBOOK_ADDRESS_2 = make_evm_address()

REMOTE_ADDRESSBOOK = [
    AddressbookEntry(
        name='Remote name that doesnt conflict with anything',
        address=ADDRESSBOOK_ADDRESS_1,
        blockchain=SupportedBlockchain.ETHEREUM,
    ), AddressbookEntry(
        name='Remote name that has a conflict, and it should replace the local name',
        address=ADDRESSBOOK_ADDRESS_2,
        blockchain=SupportedBlockchain.OPTIMISM,
    ), AddressbookEntry(
        name='Remote name that has a conflict, but the local name should be preferred',
        address=ADDRESSBOOK_ADDRESS_2,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
]
SERIALIZED_REMOTE_ADDRESSBOOK = [
    {
        'address': ADDRESSBOOK_ADDRESS_1,
        'blockchain': 'ETH',
        'new_name': 'Remote name that doesnt conflict with anything',
    },
    {
        'address': ADDRESSBOOK_ADDRESS_2,
        'blockchain': 'OPTIMISM',
        'new_name': 'Remote name that has a conflict, and it should replace the local name',
        'old_name': 'Local name that has a conflict and should be replaced by the remote name',
    },
    {
        'address': ADDRESSBOOK_ADDRESS_2,
        'blockchain': 'ETH',
        'new_name': 'Remote name that has a conflict, but the local name should be preferred',
    },
]


ABI_DATA = [
    {'id': 1, 'name': 'ABI1', 'value': '[{"inputs":[{"internalType":"address","name":"_factory","type":"address"}]'},  # noqa: E501
    {'id': 2, 'name': 'ABI2', 'value': '[{"name":"BasePoolAdded","inputs":[{"name":"base_pool","type":"address","indexed":false}],"anonymous":false,"type":"event"}]'},  # noqa: E501
]
CONTRACT_DATA = [
    {'address': '0x4bBa290826C253BD854121346c370a9886d1bC26', 'chain_id': 1, 'abi': 1, 'deployed_block': 1000},  # noqa: E501
    {'address': '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'chain_id': 10, 'abi': 1, 'deployed_block': 20},  # noqa: E501
    {'address': '0x19e4057A38a730be37c4DA690b103267AAE1d75d', 'chain_id': 1, 'abi': 2, 'deployed_block': None},  # noqa: E501
]


SPAM_ASSET_MOCK_DATA = {
    'spam_assets': [
        {
            'address': ETHEREUM_SPAM_ASSET_ADDRESS,
            'name': '$ ClaimUniLP.com',
            'symbol': '$ ClaimUniLP.com - Visit to claim',
            'decimals': 18,
        },
        {
            'address': OPTIMISM_SPAM_ASSET_ADDRESS,
            'name': 'spooky-v3.xyz',
            'symbol': 'Visit https://spooky-v3.xyz and claim rewards',
            'decimals': 18,
            'chain': 'optimism',
        },
    ],
}

RPC_NODE_MOCK_DATA = {
    'rpc_nodes': [
        {
            'name': 'pocket network',
            'endpoint': 'https://eth-mainnet.gateway.pokt.network/v1/5f3453978e354ab992c4da79',
            'weight': 0.50,
            'owned': False,
            'active': True,
            'blockchain': 'ETH',
        },
        {
            'name': 'alchemy free',
            'endpoint': 'https://mainnet.optimism.io',
            'weight': 0.50,
            'owned': False,
            'active': True,
            'blockchain': 'OPTIMISM',
        },
    ],
}

CONTRACTS_MOCK_DATA = {
    'contracts': {
        'abis_data': ABI_DATA,
        'contracts_data': CONTRACT_DATA,
    },
}


def make_single_mock_github_data_response(target: UpdateType):
    """Creates a mocking function for a single update type for github requests."""
    def mock_github_data_response(url, timeout):  # pylint: disable=unused-argument
        if 'info' in url:
            data = {
                'spam_assets': {'latest': 1 if target == UpdateType.SPAM_ASSETS else 0},
                'rpc_nodes': {'latest': 1 if target == UpdateType.RPC_NODES else 0},
                'contracts': {'latest': 1 if target == UpdateType.CONTRACTS else 0},
                'global_addressbook': {'latest': 1 if target == UpdateType.GLOBAL_ADDRESSBOOK else 0},  # noqa: E501
            }
        elif 'spam_assets/v' in url:
            data = SPAM_ASSET_MOCK_DATA
        elif 'rpc_nodes/v' in url:
            data = RPC_NODE_MOCK_DATA
        elif 'contracts/v' in url:
            data = CONTRACTS_MOCK_DATA
        elif 'global_addressbook/v' in url:
            data = {'global_addressbook': SERIALIZED_REMOTE_ADDRESSBOOK}
        else:
            raise AssertionError(f'Unknown {url=} during test')

        return MockResponse(200, json.dumps(data))

    return mock_github_data_response


def make_mock_github_response(latest: int, min_version: Optional[str] = None, max_version: Optional[str] = None) -> Callable:  # noqa: E501
    """Creates a mocking function for all update types for github requests."""
    def mock_github_response(url, timeout):  # pylint: disable=unused-argument
        if 'info' in url:
            result = {}
            for update_type in UpdateType:
                entry = {'latest': latest}
                for i in range(1, latest + 1):
                    if min_version or max_version:
                        if 'limits' not in entry:  # not using defaultdict to see that if missing it's also handled by the code fine  # noqa: E501
                            entry['limits'] = {}
                        entry['limits'][i] = {}
                        if min_version:
                            entry['limits'][i]['min_version'] = min_version
                        if max_version:
                            entry['limits'][i]['max_version'] = max_version
                result[update_type.value] = entry
        elif 'spam_assets/v' in url:
            result = SPAM_ASSET_MOCK_DATA
        elif 'rpc_nodes/v' in url:
            result = RPC_NODE_MOCK_DATA
        elif 'contracts/v' in url:
            result = CONTRACTS_MOCK_DATA
        elif 'global_addressbook/v' in url:
            result = {'global_addressbook': SERIALIZED_REMOTE_ADDRESSBOOK}
        else:
            raise AssertionError(f'Unknown {url=} during test')

        return MockResponse(200, json.dumps(result))

    return mock_github_response


@pytest.fixture(name='our_version')
def fixture_our_version():
    """Allow mocking our rotki version since in CI version is 0 and hard to control"""
    return None


@pytest.fixture(name='data_updater')
def fixture_data_updater(messages_aggregator, database, our_version):
    """Initialize the DataUpdater object, optionally mocking our rotki version"""
    with ExitStack() as stack:
        if our_version is not None:
            stack.enter_context(patch('rotkehlchen.db.updates.get_current_version', return_value=VersionCheckResult(our_version=our_version)))  # noqa: E501
        return RotkiDataUpdater(
            msg_aggregator=messages_aggregator,
            user_db=database,
        )


def reset_update_type_mappings(data_updater) -> None:
    """Need to use this after mocking so that the mapping points to the mocked methods"""
    data_updater.update_type_mappings = {
        UpdateType.SPAM_ASSETS: data_updater.update_spam_assets,
        UpdateType.RPC_NODES: data_updater.update_rpc_nodes,
        UpdateType.CONTRACTS: data_updater.update_contracts,
        UpdateType.GLOBAL_ADDRESSBOOK: data_updater.update_global_addressbook,
    }


def test_update_type_mappings_is_complete(data_updater: RotkiDataUpdater) -> None:
    """Test that all UpdateType values have a mapping in RotkiDataUpdater"""
    for update_type in tuple(UpdateType):
        assert update_type in data_updater.update_type_mappings, f'{update_type} is not in the mapping'  # noqa: E501


def test_update_spam_assets(data_updater: RotkiDataUpdater) -> None:
    """
    Test that spam assets for different chains have been correctly populated
    """
    # consume warnings from other tests
    data_updater.msg_aggregator.consume_warnings()

    # check that spam assets don't exist before
    eth_spam_token_id = evm_address_to_identifier(ETHEREUM_SPAM_ASSET_ADDRESS, ChainID.ETHEREUM, EvmTokenKind.ERC20)  # noqa: E501
    op_spam_token_id = evm_address_to_identifier(OPTIMISM_SPAM_ASSET_ADDRESS, ChainID.OPTIMISM, EvmTokenKind.ERC20)  # noqa: E501
    with pytest.raises(UnknownAsset):
        EvmToken(eth_spam_token_id)
    with pytest.raises(UnknownAsset):
        EvmToken(op_spam_token_id)

    # set a high version of the globaldb to avoid conflicts with future changes
    with patch('requests.get', wraps=make_single_mock_github_data_response(UpdateType.SPAM_ASSETS)):  # noqa: E501
        data_updater.check_for_updates()

    ethereum_token = EvmToken(eth_spam_token_id)
    optimism_token = EvmToken(op_spam_token_id)

    assert ethereum_token.protocol == SPAM_PROTOCOL
    assert optimism_token.protocol == SPAM_PROTOCOL

    with data_updater.user_db.conn.read_ctx() as cursor:
        cursor.execute('SELECT identifier FROM assets WHERE identifier IN (?, ?)', (eth_spam_token_id, op_spam_token_id))  # noqa: E501
        assert cursor.fetchall() == [(eth_spam_token_id,), (op_spam_token_id,)]


def test_updates_run(data_updater: RotkiDataUpdater) -> None:
    """
    Check that the invdividual update functions execute as many times as needed
    due to latest. This is also a way to check the subsequent tests for updates
    not executing are valid
    """
    times = 2
    with ExitStack() as stack:
        stack.enter_context(patch('requests.get', wraps=make_mock_github_response(latest=times)))
        patches = [
            stack.enter_context(patch.object(data_updater, f'update_{update_type.value}'))
            for update_type in UpdateType
        ]
        reset_update_type_mappings(data_updater)
        data_updater.check_for_updates()

    assert all(patch.call_count == times for patch in patches)
    with data_updater.user_db.conn.read_ctx() as cursor:
        cursor.execute(  # make sure latest DB value is also changed
            'SELECT value from settings WHERE name IN(?, ?, ?, ?)',
            [x.serialize() for x in UpdateType],
        )
        assert {x[0] for x in cursor} == {'2'}


def test_no_update_due_to_update_version(data_updater: RotkiDataUpdater) -> None:
    """Check that the updates don't execute if we have a higher update version locally"""
    # set a higher last version applied
    with data_updater.user_db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
            [
                (UpdateType.SPAM_ASSETS.serialize(), 999),
                (UpdateType.RPC_NODES.serialize(), 999),
                (UpdateType.CONTRACTS.serialize(), 999),
                (UpdateType.GLOBAL_ADDRESSBOOK.serialize(), 999),
            ],
        )
    with ExitStack() as stack:
        stack.enter_context(patch('requests.get', wraps=make_mock_github_response(latest=1)))
        patches = [
            stack.enter_context(patch.object(data_updater, f'update_{update_type.value}'))
            for update_type in UpdateType
        ]
        reset_update_type_mappings(data_updater)
        data_updater.check_for_updates()

    assert all(patch.call_count == 0 for patch in patches)
    with data_updater.user_db.conn.read_ctx() as cursor:
        cursor.execute(  # also make sure latest DB value is not changed
            'SELECT value from settings WHERE name IN(?, ?, ?, ?)',
            [x.serialize() for x in UpdateType],
        )
        assert {x[0] for x in cursor} == {'999'}


@pytest.mark.parametrize('our_version', ['1.35.0'])  # set a normal version for CI
def test_no_update_due_to_min_rotki(data_updater: RotkiDataUpdater) -> None:
    """Check updates don't execute if there is a min rotki version requirement greater than ours"""
    with ExitStack() as stack:
        stack.enter_context(patch('requests.get', wraps=make_mock_github_response(latest=1, min_version='99.99.99')))  # noqa: E501
        patches = [
            stack.enter_context(patch.object(data_updater, f'update_{update_type.value}'))
            for update_type in UpdateType
        ]
        reset_update_type_mappings(data_updater)
        data_updater.check_for_updates()

    assert all(patch.call_count == 0 for patch in patches)
    with data_updater.user_db.conn.read_ctx() as cursor:
        cursor.execute(  # also make sure latest DB value is not changed
            'SELECT value from settings WHERE name IN(?, ?, ?, ?)',
            [x.serialize() for x in UpdateType],
        )
        assert {x[0] for x in cursor} == set()


@pytest.mark.parametrize('our_version', ['1.35.0'])  # set a normal version for CI
def test_no_update_due_to_max_rotki(data_updater: RotkiDataUpdater) -> None:
    """Check updates don't execute if there is a max rotki version requirement lower than ours"""
    with ExitStack() as stack:
        stack.enter_context(patch('requests.get', wraps=make_mock_github_response(latest=1, max_version='1.0.0')))  # noqa: E501
        patches = [
            stack.enter_context(patch.object(data_updater, f'update_{update_type.value}'))
            for update_type in UpdateType
        ]
        reset_update_type_mappings(data_updater)
        data_updater.check_for_updates()

    assert all(patch.call_count == 0 for patch in patches)
    with data_updater.user_db.conn.read_ctx() as cursor:
        cursor.execute(  # also make sure latest DB value is not changed
            'SELECT value from settings WHERE name IN(?, ?, ?, ?)',
            [x.serialize() for x in UpdateType],
        )
        assert {x[0] for x in cursor} == set()


def test_update_rpc_nodes(data_updater: RotkiDataUpdater) -> None:
    """Test that rpc nodes for different blockchains are updated correctly.."""
    # check db state of the default rpc nodes before updating
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes')
        assert cursor.fetchone()[0] == 26

    # check the db state of the user's rpc_nodes
    custom_node_tuple = ('custom node', 'https://node.rotki.com/', 1, 1, '0.50', 'ETH')
    with data_updater.user_db.user_write() as write_cursor:
        write_cursor.execute('SELECT COUNT(*) FROM rpc_nodes')
        assert write_cursor.fetchone()[0] == 26
        # add a custom node.
        write_cursor.execute(
            'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES(?, ?, ?, ?, ?, ?)',
            custom_node_tuple,
        )
        write_cursor.execute('SELECT COUNT(*) FROM rpc_nodes')
        assert write_cursor.fetchone()[0] == 27

    with patch('requests.get', wraps=make_single_mock_github_data_response(UpdateType.RPC_NODES)):
        data_updater.check_for_updates()

    # check the db state after updating
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes')
        assert cursor.fetchone()[0] == 2

    # check that 3 nodes are present in the user db including the custom node added.
    # 19 nodes were deleted since the updated rpc nodes data did not contain them.
    with data_updater.user_db.conn.read_ctx() as cursor:
        nodes = cursor.execute('SELECT * FROM rpc_nodes').fetchall()

    assert nodes == [
        (7, 'optimism official', 'https://mainnet.optimism.io', 0, 1, '0.20', 'OPTIMISM'),
        (27, *custom_node_tuple),
        (28, 'pocket network', 'https://eth-mainnet.gateway.pokt.network/v1/5f3453978e354ab992c4da79', 0, 1, '0.5', 'ETH'),  # noqa: E501
    ]


def test_update_contracts(data_updater: RotkiDataUpdater) -> None:
    """Tests functionality for remotely updating contracts"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        # Check state before the update
        cursor.execute('SELECT MAX(id) FROM contract_abi')
        initial_abis = cursor.execute('SELECT * FROM contract_abi').fetchall()
        assert len(initial_abis) > 0, 'There should be some abis in the db'
        initial_contracts = cursor.execute('SELECT * FROM contract_data').fetchall()
        assert len(initial_contracts) > 0, 'There should be some contracts in the db'

    with patch('requests.get', wraps=make_single_mock_github_data_response(UpdateType.CONTRACTS)):  # noqa: E501
        data_updater.check_for_updates()  # apply the update

    remote_id_to_local_id = {}
    with GlobalDBHandler().conn.read_ctx() as cursor:
        for entry in ABI_DATA:
            cursor.execute(
                'SELECT id FROM contract_abi WHERE name=? AND value=?',
                (entry['name'], entry['value']),
            )
            local_id = cursor.fetchone()
            assert local_id is not None
            remote_id_to_local_id[entry['id']] = local_id[0]

    expected_new_contracts = [(
        contract_data['address'],
        contract_data['chain_id'],
        remote_id_to_local_id[contract_data['abi']],
        contract_data['deployed_block'],
    ) for contract_data in CONTRACT_DATA]
    with GlobalDBHandler().conn.read_ctx() as cursor:
        # Check that the new abis and contracts were added and the old ones were not modified
        contracts_after_update = cursor.execute('SELECT * FROM contract_data')
        assert set(contracts_after_update) == set(initial_contracts) | set(expected_new_contracts)


@pytest.mark.parametrize('empty_global_addressbook', [True])
def test_global_addressbook(data_updater: RotkiDataUpdater) -> None:
    """Test that remote updates for global addressbook work"""
    db_addressbook = DBAddressbook(data_updater.user_db)
    # check state of the address book before updating
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM address_book')
        assert cursor.fetchone()[0] == 0

    # Populate addressbook and see that preferring local / remote names works as expected.
    initial_entries = [
        AddressbookEntry(
            address=ADDRESSBOOK_ADDRESS_1,
            name='Local name that does not conflict with anything',
            blockchain=SupportedBlockchain.AVALANCHE,
        ), AddressbookEntry(
            address=ADDRESSBOOK_ADDRESS_2,
            name='Local name that has a conflict with remote, but should stay as is',
            blockchain=SupportedBlockchain.ETHEREUM,
        ), AddressbookEntry(
            address=ADDRESSBOOK_ADDRESS_2,
            name='Local name that has a conflict and should be replaced by the remote name',
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
    ]
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        db_addressbook.add_addressbook_entries(
            write_cursor=write_cursor,
            entries=initial_entries,
        )

    with patch('requests.get', wraps=make_single_mock_github_data_response(UpdateType.GLOBAL_ADDRESSBOOK)):  # noqa: E501
        data_updater.check_for_updates()

    # Assert state of the address book after the update
    with GlobalDBHandler().conn.read_ctx() as cursor:
        all_entries = db_addressbook.get_addressbook_entries(cursor=cursor)

    assert set(all_entries) == set(initial_entries[:2] + REMOTE_ADDRESSBOOK[:2])
