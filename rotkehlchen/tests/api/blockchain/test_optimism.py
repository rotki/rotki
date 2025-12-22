from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

TEST_ADDY = '0x9531C059098e3d194fF87FebB587aB07B30B1306'


@pytest.mark.vcr(filter_query_parameters=['apikey'], allow_playback_repeats=True)
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('network_mocking', [False])
def test_add_optimism_blockchain_account(rotkehlchen_api_server: 'APIServer') -> None:
    """Test adding an optimism account when there is none in the db
    works as expected and that balances are returned and tokens are detected.
    """
    optimism_chain_key = SupportedBlockchain.OPTIMISM.serialize()
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain=optimism_chain_key,
        ),
        json={
            'accounts': [{'address': TEST_ADDY}],
        },
    )
    assert_proper_response(response)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain=optimism_chain_key,
    ))
    result = assert_proper_sync_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][optimism_chain_key][TEST_ADDY]
    assert 'liabilities' in account_balances
    asset_eth = account_balances['assets'][A_ETH.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(asset_eth['amount']) >= ZERO
    assert FVal(asset_eth['value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    total_eth = result['totals']['assets'][A_ETH.identifier][DEFAULT_BALANCE_LABEL]
    assert FVal(total_eth['amount']) >= ZERO
    assert FVal(total_eth['value']) >= ZERO

    now = ts_now()
    # now check that detecting tokens works
    optimism_tokens = (
        Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
        Asset('eip155:10/erc20:0x4F604735c1cF31399C6E711D5962b2B3E0225AD3'),
        Asset('eip155:10/erc20:0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'),
    )
    # patch get_evm_tokens return value to just a few tokens
    # to prevent issues when the asset database changes
    with patch('rotkehlchen.chain.evm.tokens.GlobalDBHandler.get_token_detection_data',
        return_value=([
            EvmTokenDetectionData(
                identifier='eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
                address=string_to_evm_address('0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
                decimals=18,
            ),
            EvmTokenDetectionData(
                identifier='eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
                address=string_to_evm_address('0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
                decimals=6,
            ),
            EvmTokenDetectionData(
                identifier='eip155:10/erc20:0x4F604735c1cF31399C6E711D5962b2B3E0225AD3',
                address=string_to_evm_address('0x4F604735c1cF31399C6E711D5962b2B3E0225AD3'),
                decimals=18,
            ),
            EvmTokenDetectionData(
                identifier='eip155:10/erc20:0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',
                address=string_to_evm_address('0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'),
                decimals=18,
            ),
        ], []),
    ):
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'detecttokensresource',
                blockchain=optimism_chain_key,
            ),
        )
    result = assert_proper_sync_response_with_result(response)
    assert result[TEST_ADDY]['last_update_timestamp'] >= now
    assert set(result[TEST_ADDY]['tokens']) == set(optimism_tokens)

    # and query balances again to see tokens also appear
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain=optimism_chain_key,
        ),
        json={
            'ignore_cache': True,
        },
    )
    result = assert_proper_sync_response_with_result(response)

    # Check per account
    account_balances = result['per_account'][optimism_chain_key][TEST_ADDY]
    assert 'liabilities' in account_balances
    assert len(account_balances['assets']) == len(optimism_tokens) + 1
    for asset_id in (A_ETH.identifier, *optimism_tokens):
        asset = account_balances['assets'][asset_id][DEFAULT_BALANCE_LABEL]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['value']) >= ZERO

    # Check totals
    assert 'liabilities' in result['totals']
    assert len(result['totals']['assets']) == len(optimism_tokens) + 1
    for asset_id in ('ETH', *optimism_tokens):
        asset = result['totals']['assets'][asset_id][DEFAULT_BALANCE_LABEL]
        assert FVal(asset['amount']) >= ZERO
        assert FVal(asset['value']) >= ZERO
