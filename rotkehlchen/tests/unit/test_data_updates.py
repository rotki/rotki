import json
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.updates import RotkiDataUpdater, UpdateType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import SPAM_PROTOCOL, ChainID, EvmTokenKind

ETHEREUM_SPAM_ASSET_ADDRESS = make_evm_address()
OPTIMISM_SPAM_ASSET_ADDRESS = make_evm_address()


def mock_github_data_response(url, timeout):  # pylint: disable=unused-argument
    if 'info' in url:
        return MockResponse(200, '{"spam_assets":{"latest":1}}')
    if 'spam_assets/assets_v' in url:
        data = {
            'assets': [
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

    raise AssertionError(f'Unexpected url {url} called')


def mock_github_data_response_old_update(url, timeout):  # pylint: disable=unused-argument
    if 'info' not in url:
        raise AssertionError(f'Unexpected url {url} called')

    return MockResponse(200, '{"spam_assets":{"latest":1}}')


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
    # set a higer last version applied
    with data_updater.user_db.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES (?, ?)',
            (UpdateType.SPAM_ASSETS.serialize(), 999),
        )

    with (
        patch('requests.get', wraps=mock_github_data_response_old_update),
        patch.object(data_updater, 'update_spam_assets') as spam_assets,
    ):
        data_updater.check_for_updates()
        assert spam_assets.call_count == 0
