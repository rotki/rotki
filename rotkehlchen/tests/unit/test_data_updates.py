import json
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.updates import RotkiDataUpdater, UpdateType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, EvmTokenKind

ETHEREUM_SPAM_ASSET_ADDRESS = make_evm_address()
OPTIMISM_SPAM_ASSET_ADDRESS = make_evm_address()


def mock_github_data_response(url, timeout):  # pylint: disable=unused-argument
    if 'info' in url:
        return MockResponse(200, '{"spam_assets":{"latest":1},"rpc_nodes":{"latest":1}}')
    if 'spam_assets/v' in url:
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
        return MockResponse(200, json.dumps(data))
    if 'rpc_nodes/v' in url:
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
        return MockResponse(200, json.dumps(data))

    raise AssertionError(f'Unexpected url {url} called')


def mock_github_data_response_old_update(url, timeout):  # pylint: disable=unused-argument
    if 'info' not in url:
        raise AssertionError(f'Unexpected url {url} called')

    return MockResponse(200, '{"spam_assets":{"latest":1}, "rpc_nodes": {"latest":1}}')


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
    with patch('requests.get', wraps=mock_github_data_response):
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
            ],
        )

    with (
        patch('requests.get', wraps=mock_github_data_response_old_update),
        patch.object(data_updater, 'update_spam_assets') as spam_assets,
        patch.object(data_updater, 'update_rpc_nodes') as rpc_nodes,
    ):
        data_updater.check_for_updates()
        assert spam_assets.call_count == 0
        assert rpc_nodes.call_count == 0


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

    with patch('requests.get', wraps=mock_github_data_response):
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
