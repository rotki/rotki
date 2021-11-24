import os
import random
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.chain.ethereum.structures import Eth2Validator
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='SLOW TEST -- run locally from time to time',
)
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_query_eth2_info(rotkehlchen_api_server, ethereum_accounts):
    """This test uses real data and queries the eth2 deposits"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=[],
        original_queries=['logs', 'transactions', 'blocknobytime', 'beaconchain'],
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakedetailsresource',
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
            )
            assert outcome['message'] == ''
            details = outcome['result']
        else:
            details = assert_proper_response_with_result(response)

    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakedepositsresource',
            ), json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 10,
            )
            assert outcome['message'] == ''
            deposits = outcome['result']
        else:
            deposits = assert_proper_response_with_result(response)

    expected_pubkey = '0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'  # noqa: E501
    assert deposits[0] == {
        'from_address': '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
        'tx_index': 15,
        'pubkey': expected_pubkey,
        'timestamp': 1604506685,
        'tx_hash': '0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
        'value': {'amount': '32', 'usd_value': '32'},
        'withdrawal_credentials': '0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
    }
    assert FVal(details[0]['balance']['amount']) >= ZERO
    assert FVal(details[0]['balance']['usd_value']) >= ZERO
    assert details[0]['eth1_depositor'] == '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397'  # noqa: E501
    assert details[0]['index'] == 9
    assert details[0]['public_key'] == expected_pubkey
    for duration in ('1d', '1w', '1m', '1y'):
        performance = details[0][f'performance_{duration}']
        # Can't assert for positive since they may go offline for a day and the test will fail
        # https://twitter.com/LefterisJP/status/1361091757274972160
        assert FVal(performance['amount']) is not None
        assert FVal(performance['usd_value']) is not None


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
def test_query_eth2_inactive(rotkehlchen_api_server, ethereum_accounts):
    """Test that quering eth2 module while it's not active properly errors"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=[],
        original_queries=['logs', 'transactions', 'blocknobytime', 'beaconchain'],
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakedetailsresource',
            ),
        )
        assert_error_response(
            response=response,
            contained_in_msg='Cant query eth2 staking details since eth2 module is not active',
            status_code=HTTPStatus.CONFLICT,
        )


@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_add_get_delete_eth2_validators(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == []

    validators = [Eth2Validator(
        index=4235,
        public_key='0xadd548bb2e6962c255ec5420e40e6e506dfc936592c700d56718ada7dcc52e4295644ff8f94f4ef898aa8a5ad81a5b84',  # noqa: E501
    ), Eth2Validator(
        index=5235,
        public_key='0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb',  # noqa: E501
    ), Eth2Validator(
        index=23948,
        public_key='0x8a569c702a5b51894a25b261960f6b792aa35f8f67d9e1d96a52b15857cf0ee4fa30670b9bfca40e9a9dba81057ba4c7',  # noqa: E501
    ), Eth2Validator(
        index=43948,
        public_key='0x922127b0722e0fca3ceeffe78a6d2f91f5b78edff42b65cce438f5430e67f389ff9f8f6a14a26ee6467051ddb1cc21eb',  # noqa: E501
    )]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[0].index},
    )
    assert_simple_ok_response(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': validators[1].public_key},
    )
    assert_simple_ok_response(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[2].index, 'public_key': validators[2].public_key},
    )
    assert_simple_ok_response(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': validators[3].public_key[2:]},  # skip 0x and see it works
    )
    assert_simple_ok_response(response)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [x.serialize() for x in validators]

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': validators[0].public_key},
    )
    assert_simple_ok_response(response)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[2].index},
    )
    assert_simple_ok_response(response)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[3].index, 'public_key': validators[3].public_key},
    )
    assert_simple_ok_response(response)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [validators[1].serialize()]


@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_add_delete_validator_errors(rotkehlchen_api_server, method):
    """Tests the error cases of adding/deleting a validator"""
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Need to provide either a validator index or a public key for an eth2 validator',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': -1},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Validator index must be an integer >= 0',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 999957426},
    )
    if method == 'PUT':
        msg = 'Validator data for 999957426 could not be found. Likely invalid validator'  # noqa: E501
        status_code = HTTPStatus.BAD_GATEWAY
    else:  # DELETE
        msg = 'Tried to delete eth2 validator with validator_index 999957426 from the DB but it did not exist'  # noqa: E501
        status_code = HTTPStatus.CONFLICT
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=status_code,
    )
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': 'fooboosoozloklkl'},  # noqa: E501
    )
    assert_error_response(
        response=response,
        contained_in_msg='The given eth2 public key fooboosoozloklkl is not valid hex',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': '0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fbcd'},  # noqa: E501
    )
    assert_error_response(
        response=response,
        contained_in_msg='The given eth2 public key 0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fbcd has 49 bytes. Expected 48',  # noqa: E501
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # and now add a validator and try to re-add it
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 5235, 'public_key': '0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb'},  # noqa: E501
    )
    assert_simple_ok_response(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 5235, 'public_key': '0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb'},  # noqa: E501
    )
    assert_error_response(
        response=response,
        contained_in_msg='Validator 5235 already exists in the DB',
        status_code=HTTPStatus.CONFLICT,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 5235},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Validator 5235 already exists in the DB',
        status_code=HTTPStatus.CONFLICT,
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': '0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb'},  # noqa: E501
    )
    assert_error_response(
        response=response,
        contained_in_msg='Validator 0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb already exists in the DB',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('query_all_balances', [False, True])
def test_query_eth2_balances(rotkehlchen_api_server, query_all_balances):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == []

    validators = [Eth2Validator(
        index=4235,
        public_key='0xadd548bb2e6962c255ec5420e40e6e506dfc936592c700d56718ada7dcc52e4295644ff8f94f4ef898aa8a5ad81a5b84',  # noqa: E501
    ), Eth2Validator(
        index=5235,
        public_key='0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb',  # noqa: E501
    )]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[0].index},
    )
    assert_simple_ok_response(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'public_key': validators[1].public_key},
    )
    assert_simple_ok_response(response)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [x.serialize() for x in validators]

    async_query = random.choice([False, True])
    if query_all_balances:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ), json={'async_query': async_query})
    else:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'named_blockchain_balances_resource',
            blockchain='ETH2',
        ), json={'async_query': async_query})

    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task_with_result(
            server=rotkehlchen_api_server,
            task_id=task_id,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
        )
    else:
        outcome = assert_proper_response_with_result(response)

    assert len(outcome['per_account']) == 1  # only ETH2
    per_acc = outcome['per_account']['ETH2']
    assert len(per_acc) == 2
    # hope they don't get slashed ;(
    amount1 = FVal('34.547410412')
    amount2 = FVal('34.600348623')
    assert FVal(per_acc[validators[0].public_key]['assets']['ETH2']['amount']) >= amount1
    assert FVal(per_acc[validators[1].public_key]['assets']['ETH2']['amount']) >= amount2
    totals = outcome['totals']
    assert len(totals['assets']) == 1
    assert len(totals['liabilities']) == 0
    assert FVal(totals['assets']['ETH2']['amount']) >= amount1 + amount2
