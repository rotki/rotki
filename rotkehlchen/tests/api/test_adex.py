import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.adex.types import Bond, ChannelWithdraw, Unbond
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ADX
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances

ADEX_TEST_ADDR = string_to_evm_address('0x8Fe178db26ebA2eEdb22575265bf10A63c395a3d')


@pytest.mark.parametrize('ethereum_accounts', [[ADEX_TEST_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'adexbalancesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='adex module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [[ADEX_TEST_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['adex']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_balances_premium(
    rotkehlchen_api_server,
    ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test get balances for premium users works as expected"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        # original_queries=['adex_staking'],
        extra_flags=['mocked_adex_staking_balance'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'adexbalancesresource'),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(
            UserWarning(f'Test account {ADEX_TEST_ADDR} has no balances'),
        )
        return

    assert FVal(result[ADEX_TEST_ADDR][0]['adx_balance']['amount']) == FVal('113547.9817118382760270384899')  # noqa: E501
    assert result[ADEX_TEST_ADDR][0]['adx_balance']['usd_value'] is not None


@pytest.mark.skip('Needs to be fixed by Victor after the changes to the subgraph')
@pytest.mark.parametrize('ethereum_accounts', [[ADEX_TEST_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['adex']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(2)])
def test_get_events(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'adexhistoryresource'),
            json={'async_query': async_query, 'to_timestamp': 1611747322},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    identity_address = '0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204'
    tom_pool_id = '0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28'
    bond_id = '0x540cab9883923c01e657d5da4ca5674b6e4626b4a148224635495502d674c7c5'
    channel_id = '0x30d87bab0ef1e7f8b4c3b894ca2beed41bbd54c481f31e5791c1e855c9dbf4ba'
    result = result[ADEX_TEST_ADDR]
    expected_events = [Bond(
        tx_hash='0x9989f47c6c0a761f98f910ac24e2438d858be96c12124a13be4bb4b3150c55ea',
        address=ADEX_TEST_ADDR,
        identity_address=identity_address,
        timestamp=1604366004,
        bond_id=bond_id,
        pool_id=tom_pool_id,
        value=Balance(FVal(100000), FVal(200000)),
        nonce=0,
        slashed_at=0,
    ), ChannelWithdraw(
        tx_hash='0xa9ee91af823c0173fc5ada908ff9fe3f4d7c84a2c9da795f0889b3f4ace75b13',
        address=ADEX_TEST_ADDR,
        identity_address=identity_address,
        timestamp=1607453764,
        channel_id=channel_id,
        pool_id=tom_pool_id,
        value=Balance(FVal('5056.894263641728544592'), FVal('10113.788527283457089184')),
        token=A_ADX,
        log_index=316,
    ), Unbond(
        tx_hash='0xa9ee91af823c0173fc5ada908ff9fe3f4d7c84a2c9da795f0889b3f4ace75b13',
        address=ADEX_TEST_ADDR,
        identity_address=identity_address,
        timestamp=1607453764,
        bond_id=bond_id,
        pool_id=tom_pool_id,
        value=Balance(FVal(100000), FVal(200000)),
    )]
    assert len(result['events']) == 8
    assert result['events'][:len(expected_events)] == [x.serialize() for x in expected_events]
    assert 'staking_details' in result
    # Make sure events end up in the DB
    assert len(rotki.data.db.get_adex_events()) != 0
    # test adex data purging from the db works
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'namedethereummoduledataresource',
        module_name='adex',
    ))
    assert_simple_ok_response(response)
    assert len(rotki.data.db.get_adex_events()) == 0
