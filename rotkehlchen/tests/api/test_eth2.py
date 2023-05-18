import os
import random
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.eth2.eth2 import FREE_VALIDATORS_LIMIT
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
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
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='SLOW TEST -- run locally from time to time',
)
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_query_eth2_deposits_details_and_stats(rotkehlchen_api_server, ethereum_accounts):
    """This test uses real data and queries the eth2 details, deposits and daily stats"""
    # first check that the endpoint for profit can be correctly queried
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2stakedetailsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert FVal(result['withdrawn_consensus_layer_rewards']) == ZERO
    assert FVal(result['execution_layer_rewards']) == ZERO

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
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakedetailsresource',
            ), json={'async_query': async_query, 'ignore_cache': True},
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

    expected_pubkey = '0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'  # noqa: E501
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

    # for daily stats let's have 3 validators
    new_index_1 = 43948
    new_index_2 = 23948
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': new_index_1},
    )
    assert_simple_ok_response(response)
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': new_index_2},
    )
    assert_simple_ok_response(response)

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    # Now query eth2 details also including manually input validators to see they work
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2stakedetailsresource',
        ), json={'async_query': async_query, 'ignore_cache': True},
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

    # The 2 new validators along with their depositor details should be there
    assert len(details) >= 6
    assert details[0]['index'] == 9  # already checked above
    assert details[1]['index'] == new_index_2
    # TODO: This used to be 0x234EE9e35f8e9749A002fc42970D570DB716453B but now without queried events we got nothing: # noqa: E501
    assert details[1]['eth1_depositor'] is None
    assert details[2]['index'] == new_index_1
    # TODO: This used to be 0xc2288B408Dc872A1546F13E6eBFA9c94998316a2 but now without queried events we got nothing: # noqa: E501
    assert details[2]['eth1_depositor'] is None

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    # Now query eth2 details using filters
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2stakedetailsresource',
        ), json={
            'async_query': async_query,
            'ignore_cache': False,
            'validator_indices': [new_index_1],
        },
    )
    details = assert_proper_response_with_result(response)
    assert len(details) == 1
    assert details[0]['index'] == new_index_1

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    # query daily stats, first without cache -- requesting all
    json = {'only_cache': False}
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json=json,
    )
    result = assert_proper_response_with_result(response)
    total_stats = len(result['entries'])
    assert total_stats == result['entries_total']
    assert total_stats == result['entries_found']
    full_sum_pnl = FVal(result['sum_pnl']['amount'])
    full_sum_usd_value = FVal(result['sum_pnl']['usd_value'])
    calculated_sum_pnl = ZERO
    calculated_sum_usd_value = ZERO
    for entry in result['entries']:
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
        calculated_sum_usd_value += FVal(entry['pnl']['usd_value'])
    assert full_sum_pnl.is_close(calculated_sum_pnl)
    assert full_sum_usd_value.is_close(calculated_sum_usd_value)

    # filter by validator_index
    queried_validators = [new_index_1, 9]
    json = {'only_cache': True, 'validators': queried_validators}
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json=json,
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] <= total_stats
    assert all(x['validator_index'] in queried_validators for x in result['entries'])

    # filter by validator_index and timestamp
    queried_validators = [new_index_1, 9]
    from_ts = 1613779200
    to_ts = 1632182400
    json = {'only_cache': True, 'validators': queried_validators, 'from_timestamp': from_ts, 'to_timestamp': to_ts}  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json=json,
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] <= total_stats
    assert len(result['entries']) == result['entries_found']
    full_sum_pnl = FVal(result['sum_pnl']['amount'])
    full_sum_usd_value = FVal(result['sum_pnl']['usd_value'])
    calculated_sum_pnl = ZERO
    calculated_sum_usd_value = ZERO
    next_page_times = []
    for idx, entry in enumerate(result['entries']):
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
        calculated_sum_usd_value += FVal(entry['pnl']['usd_value'])
        assert entry['validator_index'] in queried_validators
        time = entry['timestamp']
        assert time >= from_ts
        assert time <= to_ts

        if 5 <= idx <= 9:
            next_page_times.append(time)

        if idx >= result['entries_found'] - 1:
            continue
        assert entry['timestamp'] >= result['entries'][idx + 1]['timestamp']
    assert full_sum_pnl.is_close(calculated_sum_pnl)
    assert full_sum_usd_value.is_close(calculated_sum_usd_value)

    # filter by validator_index and timestamp and add pagination
    json = {'only_cache': True, 'validators': queried_validators, 'from_timestamp': from_ts, 'to_timestamp': to_ts, 'limit': 5, 'offset': 5}  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json=json,
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] <= total_stats
    assert len(result['entries']) == 5
    # Check the sum pnl values here and see that they include only values from the current page
    full_sum_pnl = FVal(result['sum_pnl']['amount'])
    full_sum_usd_value = FVal(result['sum_pnl']['usd_value'])
    calculated_sum_pnl = ZERO
    calculated_sum_usd_value = ZERO
    for idx, entry in enumerate(result['entries']):
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
        calculated_sum_usd_value += FVal(entry['pnl']['usd_value'])
        assert entry['validator_index'] in queried_validators
        time = entry['timestamp']
        assert time >= from_ts
        assert time <= to_ts

        if idx <= 4:
            assert time == next_page_times[idx]
    assert full_sum_pnl.is_close(calculated_sum_pnl)
    assert full_sum_usd_value.is_close(calculated_sum_usd_value)


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='SLOW TEST -- run locally from time to time',
)
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_eth2_add_eth1_account(rotkehlchen_api_server):
    """This test uses real data and tests that adding an ETH1 address with
    ETH2 deposits properly detects validators"""
    new_account = '0xa966B0eabCD717fa28Bd165F1cE160E7057FA369'
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=[new_account],
        btc_accounts=[],
        original_queries=['logs', 'transactions', 'blocknobytime', 'beaconchain'],
    )
    with ExitStack() as stack:
        setup.enter_blockchain_patches(stack)
        data = {'accounts': [{'address': new_account}], 'async_query': async_query}
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'blockchainsaccountsresource',
            blockchain='ETH',
        ), json=data)

        if async_query:
            task_id = assert_ok_async_response(response)
            result = wait_for_async_task_with_result(
                rotkehlchen_api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 4,
            )
        else:
            result = assert_proper_response_with_result(response)

        # now get all detected validators
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'eth2validatorsresource',
            ),
        )
        result = assert_proper_response_with_result(response)
        # That address has only 1 validator. If that changes in the future this
        # test will fail and we will need to adjust the test
        validator_pubkey = '0x800199f8f3af15a22c42ccd7185948870eceeba2d06199ea30e7e28eb976a69284e393ba2f401e8983d011534b303a57'  # noqa: E501
        assert len(result['entries']) == 1
        assert result['entries'][0] == {
            'validator_index': 227858,
            'public_key': validator_pubkey,
            'ownership_percentage': '100.00',
        }
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ))
        result = assert_proper_response_with_result(response)
        per_acc = result['per_account']
        assert FVal(per_acc['eth'][new_account]['assets'][A_ETH.identifier]['amount']) > ZERO
        assert FVal(per_acc['eth2'][validator_pubkey]['assets'][A_ETH2.identifier]['amount']) > FVal('32')  # noqa: E501
        totals = result['totals']['assets']
        assert FVal(totals['eth']['amount']) > ZERO
        assert FVal(totals['eth2']['amount']) > FVal('32')


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
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
        response = requests.put(
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
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_add_get_edit_delete_eth2_validators(rotkehlchen_api_server, start_with_valid_premium):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    expected_limit = -1 if start_with_valid_premium else FREE_VALIDATORS_LIMIT
    result = assert_proper_response_with_result(response)
    assert result == {'entries': [], 'entries_limit': expected_limit, 'entries_found': 0}

    validators = [Eth2Validator(
        index=4235,
        public_key='0xadd548bb2e6962c255ec5420e40e6e506dfc936592c700d56718ada7dcc52e4295644ff8f94f4ef898aa8a5ad81a5b84',  # noqa: E501
        ownership_proportion=ONE,
    ), Eth2Validator(
        index=5235,
        public_key='0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb',  # noqa: E501
        ownership_proportion=ONE,
    ), Eth2Validator(
        index=23948,
        public_key='0x8a569c702a5b51894a25b261960f6b792aa35f8f67d9e1d96a52b15857cf0ee4fa30670b9bfca40e9a9dba81057ba4c7',  # noqa: E501
        ownership_proportion=ONE,
    ), Eth2Validator(
        index=43948,
        public_key='0x922127b0722e0fca3ceeffe78a6d2f91f5b78edff42b65cce438f5430e67f389ff9f8f6a14a26ee6467051ddb1cc21eb',  # noqa: E501
        ownership_proportion=ONE,
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
    assert result == {'entries': [x.serialize() for x in validators], 'entries_limit': expected_limit, 'entries_found': 4}  # noqa: E501

    if start_with_valid_premium is False:
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'eth2validatorsresource',
            ), json={'validator_index': 545},
        )
        assert_error_response(
            response=response,
            contained_in_msg='Adding validator 545 None would take you over the free',
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    database = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    dbevents = DBHistoryEvents(database)
    events = [
        EthDepositEvent(
            identifier=1,
            tx_hash=make_evm_tx_hash(),
            validator_index=validators[0].index,
            sequence_index=1,
            timestamp=TimestampMS(1601379127000),
            balance=Balance(FVal(32)),
            depositor=make_evm_address(),
        ), EthWithdrawalEvent(
            identifier=2,
            validator_index=validators[0].index,
            timestamp=TimestampMS(1611379127000),
            balance=Balance(FVal('0.01')),
            withdrawal_address=make_evm_address(),
            is_exit=False,
        ), EthBlockEvent(
            identifier=3,
            validator_index=validators[2].index,
            timestamp=TimestampMS(1671379127000),
            balance=Balance(FVal(1)),
            fee_recipient=make_evm_address(),
            block_number=42,
            is_mev_reward=True,
        )]
    with database.user_write() as cursor:
        dbevents.add_history_events(cursor, events)

    with database.conn.read_ctx() as cursor:  # assert events are in the DB
        assert events == dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validators': [validators[0].index, validators[2].index]},
    )
    assert_simple_ok_response(response)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validators': [validators[3].index]},
    )
    assert_simple_ok_response(response)

    # after deleting validator indices, make sure their events are also gone
    with database.conn.read_ctx() as cursor:
        assert [events[0]] == dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
        )

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {'entries': [validators[1].serialize()], 'entries_limit': expected_limit, 'entries_found': 1}  # noqa: E501

    # Try to add validator with a custom ownership percentage
    custom_percentage_validators = [
        Eth2Validator(
            index=5235,
            public_key='0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb',  # noqa: E501
            ownership_proportion=FVal(0.4025),
        ),
        Eth2Validator(
            index=43948,
            public_key='0x922127b0722e0fca3ceeffe78a6d2f91f5b78edff42b65cce438f5430e67f389ff9f8f6a14a26ee6467051ddb1cc21eb',  # noqa: E501
            ownership_proportion=FVal(0.5),
        ),
    ]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={
            'validator_index': custom_percentage_validators[1].index,
            'public_key': custom_percentage_validators[1].public_key,
            'ownership_percentage': 50,
        },
    )
    assert_simple_ok_response(response)

    # Edit the second validator
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={
            'validator_index': 5235,
            'ownership_percentage': 40.25,
        },
    )
    assert_simple_ok_response(response)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {'entries': [validator.serialize() for validator in custom_percentage_validators], 'entries_limit': expected_limit, 'entries_found': 2}  # noqa: E501


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
    if method == 'PUT':
        msg = 'Need to provide either a validator index or a public key for an eth2 validator'  # noqa: E501
    else:
        msg = 'Missing data for required field.'

    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    invalid_index = {'validator_index': -1}
    if method == 'DELETE':
        invalid_index = {'validators': [-1]}
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json=invalid_index,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Validator index must be an integer >= 0',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    unknown_index = {'validator_index': 999957426}
    if method == 'DELETE':
        unknown_index = {'validators': [999957426]}
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json=unknown_index,
    )
    if method == 'PUT':
        msg = 'Validator data for 999957426 could not be found. Likely invalid validator'  # noqa: E501
        status_code = HTTPStatus.BAD_GATEWAY
    else:  # DELETE
        msg = 'Tried to delete eth2 validator/s with indices [999957426] from the DB but at least one of them did not exist'  # noqa: E501
        status_code = HTTPStatus.CONFLICT
    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=status_code,
    )

    if method == 'PUT':
        unknown_public_key = {'public_key': 'fooboosoozloklkl'}
        response = requests.request(
            method=method,
            url=api_url_for(
                rotkehlchen_api_server,
                'eth2validatorsresource',
            ), json=unknown_public_key,
        )
        assert_error_response(
            response=response,
            contained_in_msg='The given eth2 public key fooboosoozloklkl is not valid hex',  # noqa: E501
            status_code=HTTPStatus.BAD_REQUEST,
        )
        invalid_hex = {'public_key': '0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fbcd'}  # noqa: E501
        response = requests.request(
            method=method,
            url=api_url_for(
                rotkehlchen_api_server,
                'eth2validatorsresource',
            ), json=invalid_hex,
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
    ownership_proportion = FVal(0.45)
    base_amount = FVal(32)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {'entries': [], 'entries_limit': -1, 'entries_found': 0}

    validators = [Eth2Validator(
        index=4235,
        public_key='0xadd548bb2e6962c255ec5420e40e6e506dfc936592c700d56718ada7dcc52e4295644ff8f94f4ef898aa8a5ad81a5b84',  # noqa: E501
        ownership_proportion=ONE,
    ), Eth2Validator(
        index=5235,
        public_key='0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb',  # noqa: E501
        ownership_proportion=ownership_proportion,
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
        ), json={'public_key': validators[1].public_key, 'ownership_percentage': '45'},
    )
    assert_simple_ok_response(response)

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == {'entries': [x.serialize() for x in validators], 'entries_limit': -1, 'entries_found': 2}  # noqa: E501

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
    per_acc = outcome['per_account']['eth2']
    assert len(per_acc) == 2
    # hope they don't get slashed ;(
    amount_proportion = FVal('34.600348623') * ownership_proportion
    assert FVal(per_acc[validators[0].public_key]['assets']['ETH2']['amount']) >= base_amount
    assert FVal(per_acc[validators[1].public_key]['assets']['ETH2']['amount']) >= amount_proportion
    totals = outcome['totals']
    assert len(totals['assets']) == 1
    assert len(totals['liabilities']) == 0
    assert FVal(totals['assets']['ETH2']['amount']) >= base_amount + amount_proportion

    # now add 1 more validator and query ETH2 balances again to see it's included
    # the reason for this is to see the cache is properly invalidated at addition
    v0_pubkey = '0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95'  # noqa: E501
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 0, 'public_key': v0_pubkey},
    )
    assert_simple_ok_response(response)
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain='ETH2',
    ), json={'async_query': False, 'ignore_cache': True})
    outcome = assert_proper_response_with_result(response)

    assert len(outcome['per_account']) == 1  # only ETH2
    per_acc = outcome['per_account']['eth2']
    assert len(per_acc) == 3
    amount_proportion = FVal('34.600348623') * ownership_proportion
    assert FVal(per_acc[v0_pubkey]['assets']['ETH2']['amount']) >= base_amount
    assert FVal(per_acc[validators[0].public_key]['assets']['ETH2']['amount']) >= base_amount
    assert FVal(per_acc[validators[1].public_key]['assets']['ETH2']['amount']) >= amount_proportion
    totals = outcome['totals']
    assert len(totals['assets']) == 1
    assert len(totals['liabilities']) == 0
    assert FVal(totals['assets']['ETH2']['amount']) >= 2 * base_amount + amount_proportion


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('have_decoders', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b']])
@pytest.mark.freeze_time('2023-04-26 12:38:23 GMT')
def test_query_combined_mev_reward_and_block_production_events(rotkehlchen_api_server: 'APIServer') -> None:  # noqa: E501
    """Tests that combining mev rewards with block production events is seen by the API"""
    vindex1 = 45555
    vindex2 = 54333
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    tx_hash = deserialize_evm_tx_hash('0x8d0969db1e536969ba2e29abf8e8945e4304d49ae14523b66cbe9be5d52df804')  # noqa: E501
    block_number = 15824493
    mev_reward = '0.126458404824519798'

    # add validator data and query transaction and decode events for a single MEV reward
    response = requests.put(
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': vindex1},
    )
    assert_simple_ok_response(response)
    response = requests.put(
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': vindex2},
    )
    assert_simple_ok_response(response)

    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM eth2_validators').fetchone() == (2,)
    _, _ = get_decoded_events_of_transaction(
        evm_inquirer=rotki.chains_aggregator.ethereum.node_inquirer,
        database=rotki.data.db,
        tx_hash=tx_hash,
    )

    # query block production events. This also runs the combining code
    response = requests.post(
        url=api_url_for(
            rotkehlchen_api_server,
            'eventsonlinequeryresource',
        ), json={'query_type': 'block_productions'},
    )
    assert_simple_ok_response(response)

    # query rotki events and check they are as expected
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': True},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == result['entries_found'] == result['entries_total'] == 7
    event_identifier = None
    for entry in result['entries']:
        if entry['entry']['block_number'] == block_number:
            assert entry['grouped_events_num'] == 3
            event_identifier = entry['entry']['event_identifier']
        elif entry['entry']['block_number'] in (17055026, 16589592, 15938405):
            assert entry['grouped_events_num'] == 2
        elif entry['entry']['block_number'] in (16135531, 15849710, 15798693):
            assert entry['grouped_events_num'] == 1

    # now query the events of the combined group
    assert event_identifier is not None
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'group_by_event_ids': False, 'event_identifiers': [event_identifier]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == result['entries_found'] == 3
    assert result['entries_total'] == 12
    for outer_entry in result['entries']:
        entry = outer_entry['entry']
        if entry['sequence_index'] == 0:
            assert entry['identifier'] == 10
            assert entry['event_identifier'] == event_identifier
            assert entry['entry_type'] == 'eth block event'
            assert entry['event_type'] == 'staking'
            assert entry['event_subtype'] == 'block production'
            assert entry['validator_index'] == vindex1
            assert entry['balance']['amount'] == '0.126419309459217215'
        elif entry['sequence_index'] == 1:
            assert entry['identifier'] == 11
            assert entry['event_identifier'] == event_identifier
            assert entry['entry_type'] == 'eth block event'
            assert entry['event_type'] == 'staking'
            assert entry['event_subtype'] == 'mev reward'
            assert entry['validator_index'] == vindex1
            assert entry['balance']['amount'] == mev_reward
        elif entry['sequence_index'] == 2:
            assert entry['identifier'] == 1
            assert entry['event_identifier'] == event_identifier
            assert entry['entry_type'] == 'evm event'
            assert entry['balance']['amount'] == mev_reward
            assert entry['tx_hash'] == tx_hash.hex()  # pylint: disable=no-member
            assert entry['notes'] == f'Receive {mev_reward} ETH from 0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990 as mev reward for block {block_number}'  # noqa: E501
        else:
            raise AssertionError('Should not get to this sequence index')

    # Also check that querying by validator indices work
    assert event_identifier is not None
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'validator_indices': [vindex1, 42]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 8
    for entry in result['entries']:
        assert entry['entry']['entry_type'] == 'eth block event'
        assert entry['entry']['validator_index'] == vindex1

    # Also check that querying by ETH2 counterparty implements the exception of querying
    # all staking entry types
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'counterparties': [CPT_ETH2]},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 11
    for entry in result['entries']:
        assert entry['entry']['entry_type'] == 'eth block event'

    # check that filtering by entry_types works properly with include behaviour (default)
    assert event_identifier is not None
    entry_types_include_arg = {
        'values': ['eth block event'],
        # default behaviour is include
    }
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'entry_types': entry_types_include_arg},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 11
    for outer_entry in result['entries']:
        entry = outer_entry['entry']
        assert entry['entry_type'] == 'eth block event'

    # check that filtering by entry_types works properly with exclude behaviour
    assert event_identifier is not None
    entry_types_exclude_arg = {
        'values': ['eth block event'],
        'behaviour': 'exclude',
    }
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historyeventresource',
        ),
        json={'entry_types': entry_types_exclude_arg},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    for outer_entry in result['entries']:
        entry = outer_entry['entry']
        assert entry['entry_type'] != 'eth block event'
