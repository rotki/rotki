import json
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
    {'address': '0x4bBa290826C253BD854121346c370a9886d1bC26', 'chain_id': 1, 'name': 'CONTRACT1_ETH', 'abi': 1, 'deployed_block': 1000},  # noqa: E501
    {'address': '0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'chain_id': 10, 'name': 'CONTRACT1_OP', 'abi': 1, 'deployed_block': 20},  # noqa: E501
    {'address': '0x19e4057A38a730be37c4DA690b103267AAE1d75d', 'chain_id': 1, 'name': None, 'abi': 2, 'deployed_block': None},  # noqa: E501
]


def make_mock_github_data_response(target: UpdateType):
    """Creates a mocking function for github requests."""
    def mock_github_data_response(url, timeout):  # pylint: disable=unused-argument
        if 'info' in url:
            data = {
                'spam_assets': {'latest': 1 if target == UpdateType.SPAM_ASSETS else 0},
                'rpc_nodes': {'latest': 1 if target == UpdateType.RPC_NODES else 0},
                'contracts': {'latest': 1 if target == UpdateType.CONTRACTS else 0},
                'global_addressbook': {'latest': 1 if target == UpdateType.GLOBAL_ADDRESSBOOK else 0},  # noqa: E501
            }
        elif 'spam_assets/v' in url:
            data = {
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
        elif 'rpc_nodes/v' in url:
            data = {
                'rpc_nodes': [
                    {
                        'name': 'pocket network',
                        'endpoint': 'https://eth-mainnet.gateway.pokt.network/v1/5f3453978e354ab992c4da79',  # noqa: E501
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
        elif 'contracts/v' in url:
            data = {
                'contracts': {
                    'abis_data': ABI_DATA,
                    'contracts_data': CONTRACT_DATA,
                },
            }
        elif 'global_addressbook/v' in url:
            data = {'global_addressbook': SERIALIZED_REMOTE_ADDRESSBOOK}
        else:
            raise AssertionError(f'Unexpected url {url} called')

        return MockResponse(200, json.dumps(data))

    return mock_github_data_response


def mock_github_data_response_old_update(url, timeout):  # pylint: disable=unused-argument
    if 'info' not in url:
        raise AssertionError(f'Unexpected url {url} called')

    return MockResponse(200, json.dumps({
        'spam_assets': {'latest': 1},
        'rpc_nodes': {'latest': 1},
        'contracts': {'latest': 1},
        'global_addressbook': {'latest': 1},
    }))


@pytest.fixture(name='data_updater')
def fixture_data_updater(messages_aggregator, database):
    return RotkiDataUpdater(
        msg_aggregator=messages_aggregator,
        user_db=database,
    )


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
    with patch('requests.get', wraps=make_mock_github_data_response(UpdateType.SPAM_ASSETS)):
        data_updater.check_for_updates()

    ethereum_token = EvmToken(eth_spam_token_id)
    optimism_token = EvmToken(op_spam_token_id)

    assert ethereum_token.protocol == SPAM_PROTOCOL
    assert optimism_token.protocol == SPAM_PROTOCOL

    with data_updater.user_db.conn.read_ctx() as cursor:
        cursor.execute('SELECT identifier FROM assets WHERE identifier IN (?, ?)', (eth_spam_token_id, op_spam_token_id))  # noqa: E501
        assert cursor.fetchall() == [(eth_spam_token_id,), (op_spam_token_id,)]


def test_no_update_performed(data_updater: RotkiDataUpdater) -> None:
    """
    Check that the updates don't execute if we have a higher version locally
    """
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

    with (
        patch('requests.get', wraps=mock_github_data_response_old_update),
        patch.object(data_updater, 'update_spam_assets') as spam_assets,
        patch.object(data_updater, 'update_rpc_nodes') as rpc_nodes,
        patch.object(data_updater, 'update_contracts') as contracts,
        patch.object(data_updater, 'update_global_addressbook') as global_addressbook,
    ):
        data_updater.check_for_updates()
        assert spam_assets.call_count == 0
        assert rpc_nodes.call_count == 0
        assert contracts.call_count == 0
        assert global_addressbook.call_count == 0


def test_update_rpc_nodes(data_updater: RotkiDataUpdater) -> None:
    """Test that rpc nodes for different blockchains are updated correctly.."""
    # check db state of the default rpc nodes before updating
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes')
        assert cursor.fetchone()[0] == 10

    # check the db state of the user's rpc_nodes
    custom_node_tuple = ('custom node', 'https://node.rotki.com/', 1, 1, '0.50', 'ETH')
    with data_updater.user_db.user_write() as write_cursor:
        write_cursor.execute('SELECT COUNT(*) FROM rpc_nodes')
        assert write_cursor.fetchone()[0] == 10
        # add a custom node.
        write_cursor.execute(
            'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES(?, ?, ?, ?, ?, ?)',
            custom_node_tuple,
        )
        write_cursor.execute('SELECT COUNT(*) FROM rpc_nodes')
        assert write_cursor.fetchone()[0] == 11

    with patch('requests.get', wraps=make_mock_github_data_response(UpdateType.RPC_NODES)):
        data_updater.check_for_updates()

    # check the db state after updating
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute('SELECT COUNT(*) FROM default_rpc_nodes')
        assert cursor.fetchone()[0] == 2

    # check that 3 nodes are present in the user db including the custom node added.
    # 9 nodes were deleted since the updated rpc nodes data did not contain them.
    with data_updater.user_db.conn.read_ctx() as cursor:
        nodes = cursor.execute('SELECT * FROM rpc_nodes').fetchall()

    assert nodes == [
        (7, 'optimism official', 'https://mainnet.optimism.io', 0, 1, '0.20', 'OPTIMISM'),
        (11, *custom_node_tuple),
        (12, 'pocket network', 'https://eth-mainnet.gateway.pokt.network/v1/5f3453978e354ab992c4da79', 0, 1, '0.5', 'ETH'),  # noqa: E501
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

    with patch('requests.get', wraps=make_mock_github_data_response(UpdateType.CONTRACTS)):  # noqa: E501
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

    expected_new_contracts = []
    for contract_data in CONTRACT_DATA:
        expected_new_contracts.append((
            contract_data['address'],
            contract_data['chain_id'],
            contract_data['name'],
            remote_id_to_local_id[contract_data['abi']],
            contract_data['deployed_block'],
        ))

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

    with patch('requests.get', wraps=make_mock_github_data_response(UpdateType.GLOBAL_ADDRESSBOOK)):  # noqa: E501
        data_updater.check_for_updates()

    # Assert state of the address book after the update
    with GlobalDBHandler().conn.read_ctx() as cursor:
        all_entries = db_addressbook.get_addressbook_entries(cursor=cursor)

    assert set(all_entries) == set(initial_entries[:2] + REMOTE_ADDRESSBOOK[:2])
