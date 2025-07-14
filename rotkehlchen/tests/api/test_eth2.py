import random
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, Literal
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.eth2.eth2 import FREE_VALIDATORS_LIMIT
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDetailsWithStatus,
    ValidatorStatus,
    ValidatorType,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import DEFAULT_BALANCE_LABEL, ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import (
    ChainID,
    Eth2PubKey,
    EvmTransaction,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
    from rotkehlchen.types import ChecksumEvmAddress


# Validators with clean short history and different withdrawal address where only they withdrew
CLEAN_HISTORY_VALIDATOR1: Final = 1118010
CLEAN_HISTORY_VALIDATOR2: Final = 1118011
CLEAN_HISTORY_VALIDATOR3: Final = 564618  # exited
CLEAN_HISTORY_WITHDRAWAL1: Final = '0x24a81Dc9767348800852EF3625376e9238AbFA42'
CLEAN_HISTORY_WITHDRAWAL2: Final = '0xfAD07927C990a52e434909c9Bb1f0EC785a68F00'
CLEAN_HISTORY_WITHDRAWAL3: Final = '0xF368A42D316070Cd53515fBF67Ac219aa29D5FE0'


def _prepare_clean_validators(rotkehlchen_api_server: 'APIServer') -> None:
    """Populate history with clean validator data and ask for events"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    for index in (CLEAN_HISTORY_VALIDATOR1, CLEAN_HISTORY_VALIDATOR2, CLEAN_HISTORY_VALIDATOR3):
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'eth2validatorsresource',
            ), json={'validator_index': index},
        )
        assert_simple_ok_response(response)

    warnings = rotki.msg_aggregator.consume_warnings()
    errors = rotki.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0

    # Query withdrawals/block productions to get events for address matching to work
    for query_type in ('block_productions', 'eth_withdrawals'):
        response = requests.post(
            url=api_url_for(
                rotkehlchen_api_server,
                'eventsonlinequeryresource',
            ), json={'query_type': query_type},
        )
        assert_simple_ok_response(response)


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    match_on=['beaconchain_matcher'],
)
@pytest.mark.freeze_time('2024-06-20 18:18:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('ethereum_accounts', [[
    CLEAN_HISTORY_WITHDRAWAL1, CLEAN_HISTORY_WITHDRAWAL2, CLEAN_HISTORY_WITHDRAWAL3,
]])
def test_eth2_daily_stats(rotkehlchen_api_server: 'APIServer') -> None:
    """Test eth2 daily stats api endpoint along with filtering by various arguments"""
    # Patching here since I can't re-record this test and for some reason
    # 1118011 was not returned as active validator in the previous test.
    # TODO: Perhaps this should be re-recorded in a simpler way as daily stats
    # are not used much anymore. Or left as is ... for the same reason
    with patch('rotkehlchen.db.eth2.DBEth2.get_active_validator_indices', side_effect=lambda x: {1118010}):  # noqa: E501
        _prepare_clean_validators(rotkehlchen_api_server)
    # query daily stats, first without cache -- requesting all
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json={'only_cache': False},
    )
    result = assert_proper_sync_response_with_result(response)
    total_stats = len(result['entries'])
    assert total_stats == result['entries_total']
    assert total_stats == result['entries_found']
    full_sum_pnl = FVal(result['sum_pnl'])
    calculated_sum_pnl = ZERO
    for entry in result['entries']:
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
    assert full_sum_pnl.is_close(calculated_sum_pnl)

    # filter by validator index
    validator1_and_3_stats = 466
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json={'only_cache': True, 'validator_indices': [CLEAN_HISTORY_VALIDATOR1, CLEAN_HISTORY_VALIDATOR3]},  # noqa: E501
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] == validator1_and_3_stats
    assert len(result['entries']) == validator1_and_3_stats

    # filter by address
    validator_2_stats = total_stats - validator1_and_3_stats
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json={'only_cache': True, 'addresses': [CLEAN_HISTORY_WITHDRAWAL2]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] == validator_2_stats
    assert len(result['entries']) == validator_2_stats

    # filter by status
    validator_3_stats = 303
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json={'only_cache': True, 'status': 'exited'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] == validator_3_stats
    assert len(result['entries']) == validator_3_stats

    # filter by validator_index and timestamp
    queried_validators = [CLEAN_HISTORY_VALIDATOR1, CLEAN_HISTORY_VALIDATOR3]
    from_ts, to_ts = 1704397571, 1706211971
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json={'only_cache': True, 'validator_indices': queried_validators, 'from_timestamp': from_ts, 'to_timestamp': to_ts},  # noqa: E501
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] <= total_stats
    assert len(result['entries']) == result['entries_found']
    full_sum_pnl = FVal(result['sum_pnl'])
    calculated_sum_pnl = ZERO
    next_page_times = []
    for idx, entry in enumerate(result['entries']):
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
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

    # filter by validator_index and timestamp and add pagination
    json = {'only_cache': True, 'validator_indices': queried_validators, 'from_timestamp': from_ts, 'to_timestamp': to_ts, 'limit': 5, 'offset': 5}  # noqa: E501
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json=json,
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_total'] == total_stats
    assert result['entries_found'] <= total_stats
    assert len(result['entries']) == 5
    # Check sum pnl values here and see that they include more values than just the current page
    full_sum_pnl = FVal(result['sum_pnl'])
    calculated_sum_pnl = ZERO
    for idx, entry in enumerate(result['entries']):
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
        assert entry['validator_index'] in queried_validators
        time = entry['timestamp']
        assert time >= from_ts
        assert time <= to_ts

        if idx <= 4:
            assert time == next_page_times[idx]
    assert full_sum_pnl > calculated_sum_pnl

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'eth2dailystatsresource',
        ), json={'only_cache': False},
    )
    result = assert_proper_sync_response_with_result(response)
    total_stats = len(result['entries'])
    assert total_stats == result['entries_total']
    assert total_stats == result['entries_found']
    full_sum_pnl = FVal(result['sum_pnl'])
    calculated_sum_pnl = ZERO
    for entry in result['entries']:
        calculated_sum_pnl += FVal(entry['pnl']['amount'])
    assert full_sum_pnl.is_close(calculated_sum_pnl)


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    allow_playback_repeats=True,
    match_on=['beaconchain_matcher'],
)
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2cFc3fE6C747BFd91FF3F840C3a34F44339a0Dff',  # withdrawal/fee recipient address
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.freeze_time('2025-06-23 08:00:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
def test_staking_performance(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    validator_index = 1187604
    response = requests.put(api_url_for(  # track the depositor address
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json={'accounts': [{'address': '0xf93eba7D7a8C5c5c663d776e8890CB37fF5525ef'}]})
    assert_proper_sync_response_with_result(response)
    detected_validator = ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1707319895),
        validator_index=validator_index,
        public_key=Eth2PubKey('0xa2de832511231af4bf98083e68c67aa6429c8c2b08920302d1d6953298f3720c8d5ca22c08a54fffa2efab782e25dba8'),
        withdrawal_address=ethereum_accounts[0],
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    )
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'entries': [detected_validator.serialize()], 'entries_found': 1, 'entries_limit': -1}  # noqa: E501

    # Pull data for transactions where the blocks were mined. True if MEV tx recipient is tracked
    tx_hashes_and_amounts = [
        (deserialize_evm_tx_hash('0xb7c9fd48c675ece788cc992c0896d6a2928df45ac4e79842a15e9838702c22a6'), '0.060349153479296828', False),  # block 19212929 # noqa: E501
        (deserialize_evm_tx_hash('0xc6d9078959e1657767abf81c489b3315e69bee57faa4b0e3d8703e4ea4a22bde'), '0.07047850663787723', True),  # block 19933083  # noqa: E501
        # block 20377217 -- no mev with our accounts as recipient
        (deserialize_evm_tx_hash('0xae6276e768300db5576c1bd5cfbe6eee33c23c449d625982bc419f44621c78d1'), '0.023324581649728112', True),  # block 20536372  # noqa: E501
        (deserialize_evm_tx_hash('0x6e917c0d8ad974fd6d68789ec192ec0b5831a27c784331886f17e151c34b428c'), '0.05802984487013608', True),  # block 20868232  # noqa: E501
        (deserialize_evm_tx_hash('0xf30f5bdb725f8cd7bdcc42a13b8124ab24292fada066957689e443320a9f6b90'), '0.231618030402117244', False),  # block 21417107 -- ouch MEV sent to 0x0  # noqa: E501
    ]
    expected_execution_mev = ZERO
    for tx_hash, amount_str, is_tracked in tx_hashes_and_amounts:
        get_decoded_events_of_transaction(
            evm_inquirer=rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
            tx_hash=tx_hash,
        )
        if is_tracked:
            expected_execution_mev += FVal(amount_str)

    # Query withdrawals/block productions. This also runs the block combining code
    for query_type in ('block_productions', 'eth_withdrawals'):
        response = requests.post(
            url=api_url_for(
                rotkehlchen_api_server,
                'eventsonlinequeryresource',
            ), json={'query_type': query_type},
        )
        assert_simple_ok_response(response)

    # now let's go for performance
    response = requests.put(
        api_url_for(  # query performance for the validator above
            rotkehlchen_api_server,
            'eth2stakeperformanceresource',
        ),
        json={
            'limit': 999999,
            'offset': 0,
            'validator_indices': [
                detected_validator.validator_index,
            ]},
    )
    result = assert_proper_sync_response_with_result(response)
    expected_withdrawals_str, expected_outstanding_consensus_str = '1.189032694', '0.006663847'
    # we don't compare directly the dict values because they come from the database and sqlite
    # handles REAL SUM in a non-accurate way to the decimal point, plus it differs between OSes.
    expected_execution_blocks, expected_withdrawals, expected_outstanding_consensus, expected_apr = FVal('0.050711686670683926'), FVal(expected_withdrawals_str), FVal(expected_outstanding_consensus_str), FVal('0.0317901546184659628556739358605425843229450299631762824021434188231567579763669')  # noqa: E501
    expected_sum = expected_execution_blocks + expected_withdrawals + expected_execution_mev + expected_outstanding_consensus  # noqa: E501
    assert FVal(result['sums'].pop('execution_blocks')).is_close(expected_execution_blocks)
    assert FVal(result['sums'].pop('execution_mev')).is_close(expected_execution_mev)
    assert FVal(result['sums'].pop('withdrawals')).is_close(expected_withdrawals)
    assert FVal(result['sums'].pop('outstanding_consensus_pnl')).is_close(expected_outstanding_consensus)  # noqa: E501
    assert FVal(result['sums'].pop('sum')).is_close(expected_sum)
    assert FVal(result['sums'].pop('apr')).is_close(expected_apr)
    vindex = str(validator_index)
    assert FVal(result['validators'][vindex].pop('execution_blocks')).is_close(expected_execution_blocks)  # noqa: E501
    assert FVal(result['validators'][vindex].pop('execution_mev')).is_close(expected_execution_mev)
    assert FVal(result['validators'][vindex].pop('withdrawals')).is_close(expected_withdrawals)
    assert FVal(result['validators'][vindex].pop('outstanding_consensus_pnl')).is_close(expected_outstanding_consensus)  # noqa: E501
    assert FVal(result['validators'][vindex].pop('sum')).is_close(expected_sum)
    assert FVal(result['validators'][vindex].pop('apr')).is_close(expected_apr)


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    match_on=['beaconchain_matcher'],
)
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x61874850cC138e5e198d5756cF70e6EFED6aD464',  # withdrawal address of detected validator
    '0xbfEC7fc8DaC449a482b593Eb0aE28CfeAb49902c',  # withdrawal address of exited validator
    '0x4675C7e5BaAFBFFbca748158bEcBA61ef3b0a263',  # execution fee recipient for 432840
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.freeze_time('2024-09-15 09:00:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
def test_staking_performance_filtering_pagination(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    # Add ETH1 account and detect validators it deposited
    addresses = [
        '0x53DeB4aF24c7c8D04832B43C2B21fa75e50A145d',  # depositor of normal validator
        '0x7aF51C7e6ebcbb4cCC39e4C5061cb5CBfBC1F74A',  # depositor of exited validator
    ]
    data = {'accounts': [{'address': x} for x in addresses], 'async_query': False}
    response = requests.put(api_url_for(  # track the depositor address
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ETH',
    ), json=data)
    assert_proper_sync_response_with_result(response)

    # Query withdrawals/block productions
    for query_type in ('block_productions', 'eth_withdrawals'):
        response = requests.post(
            url=api_url_for(
                rotkehlchen_api_server,
                'eventsonlinequeryresource',
            ), json={'query_type': query_type},
        )
        assert_simple_ok_response(response)

    total_validators = 402
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    eth2 = rotki.chains_aggregator.get_module('eth2')
    assert eth2 is not None
    with patch.object(eth2.beacon_inquirer, 'get_balances', wraps=eth2.beacon_inquirer.get_balances) as get_balances:  # noqa: E501
        # now query performance for all validators with pagination and check validity
        page, last_validator, count = 0, 0, 0
        while True:
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'eth2stakeperformanceresource',
                ), json={'limit': 10, 'offset': 0 + page},
            )
            result = assert_proper_sync_response_with_result(response)
            assert result['entries_found'] == total_validators
            assert result['entries_total'] == total_validators
            assert len(result['validators']) in (10, 2)
            for index, entry in result['validators'].items():
                validator_index = int(index)
                count += 1
                assert validator_index > last_validator
                last_validator = validator_index
                assert all(FVal(x) > ZERO for x in entry.values())

            if count == total_validators:
                break

            page += 10

        assert get_balances.call_count == 1  # make sure cache works

    # now filter by validator state
    active_validators, exited_validators = 1, 401
    for status, expected_num in (('active', active_validators), ('exited', exited_validators)):
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'eth2stakeperformanceresource',
            ), json={'limit': 500, 'offset': 0, 'status': status},
        )
        result = assert_proper_sync_response_with_result(response)
        assert result['entries_found'] == expected_num
        assert len(result['validators']) == expected_num
        assert result['entries_total'] == total_validators

    # now filter by time range
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2stakeperformanceresource',
        ), json={'limit': 500, 'offset': 0, 'from_timestamp': 1704063600, 'to_timestamp': 1706742000},  # noqa: E501
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 313
    assert len(result['validators']) == 313
    assert result['entries_total'] == total_validators

    # now filter by a random address that should not have any association
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2stakeperformanceresource',
        ), json={'limit': 500, 'offset': 0, 'addresses': [make_evm_address()]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries_found'] == 0
    assert len(result['validators']) == 0
    assert result['entries_total'] == total_validators

    # note: This contains no MEV, since we do not pull the transactions here
    # now filter by an address that should have an association AND by a
    # validator index to see using both filters works
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2stakeperformanceresource',
        ), json={
            'limit': 500,
            'offset': 0,
            'addresses': [ethereum_accounts[0], make_evm_address()],
            'validator_indices': [432840],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    expected_result = {
        'validators': {
            '432840': {
                'withdrawals': '1.591595871',
                'sum': '1.68891977241534547',
                'exits': '0.001414388',
                'execution_blocks': '0.09590951341534547',
                'apr': '0.0391436464587952914253981459740635046779612036267745547809124733591012534768631',  # noqa: E501
            },
            '624729': {
                'withdrawals': '1.289917788',
                'sum': '1.289917788',
                'apr': '0.0300134962463827842665562028528326637310648429119334799442187646271982041209314',  # noqa: E501
            },
        },
        'sums': {
            'withdrawals': '2.881513659',
            'sum': '2.97883756041534547',
            'exits': '0.001414388',
            'execution_blocks': '0.09590951341534547',
            'apr': '0.0345785713525890378459771744134480842045130232693540173625656189931497287988972',  # noqa: E501
        },
        'entries_total': 402,
        'entries_found': 2,
    }
    assert result == expected_result


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397',
]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_eth2_inactive(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that querying eth2 module while it's not active properly errors"""
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
                'eth2stakeperformanceresource',
            ),
        )
        assert_error_response(
            response=response,
            contained_in_msg='Cant query eth2 staking performance since eth2 module is not active',
            status_code=HTTPStatus.CONFLICT,
        )


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    match_on=['beaconchain_matcher'],
)
@pytest.mark.freeze_time('2024-02-03 23:44:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [[]])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_add_get_edit_delete_eth2_validators(
        rotkehlchen_api_server: 'APIServer',
        start_with_valid_premium: bool,
) -> None:
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    expected_limit = -1 if start_with_valid_premium else FREE_VALIDATORS_LIMIT
    result = assert_proper_sync_response_with_result(response)
    assert result == {'entries': [], 'entries_limit': expected_limit, 'entries_found': 0}

    validators = [ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1606824023),
        validator_index=4235,
        public_key=Eth2PubKey('0xadd548bb2e6962c255ec5420e40e6e506dfc936592c700d56718ada7dcc52e4295644ff8f94f4ef898aa8a5ad81a5b84'),
        withdrawable_timestamp=Timestamp(1703014103),
        withdrawal_address=string_to_evm_address('0x865c05C13d422310d9421E4Da915B73E5289A6B1'),
        status=ValidatorStatus.EXITED,
        validator_type=ValidatorType.DISTRIBUTING,
    ), ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1606824023),
        validator_index=5235,
        public_key=Eth2PubKey('0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb'),
        withdrawal_address=string_to_evm_address('0x347A70cb4Ff0297102DC549B044c41bD61e22718'),
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    ), ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1607118167),
        validator_index=23948,
        public_key=Eth2PubKey('0x8a569c702a5b51894a25b261960f6b792aa35f8f67d9e1d96a52b15857cf0ee4fa30670b9bfca40e9a9dba81057ba4c7'),
        withdrawable_timestamp=Timestamp(1682832983),
        withdrawal_address=string_to_evm_address('0xf604d331d9109253fF63A00EA93DE5c0264314eF'),
        status=ValidatorStatus.EXITED,
        validator_type=ValidatorType.DISTRIBUTING,
    ), ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1609038167),
        validator_index=43948,
        public_key=Eth2PubKey('0x922127b0722e0fca3ceeffe78a6d2f91f5b78edff42b65cce438f5430e67f389ff9f8f6a14a26ee6467051ddb1cc21eb'),
        withdrawal_address=string_to_evm_address('0xfA7F89a14d005F057107755cA18345728E2E3938'),
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    )]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[0].validator_index},
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
        ), json={'validator_index': validators[2].validator_index, 'public_key': validators[2].public_key},  # noqa: E501
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
        ), json={'ignore_cache': True},
    )
    result = assert_proper_sync_response_with_result(response)
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
            validator_index=validators[0].validator_index,  # type: ignore[arg-type]  # validator indexes are defined above and will not be None
            sequence_index=1,
            timestamp=TimestampMS(1601379127000),
            amount=FVal(32),
            depositor=make_evm_address(),
        ), EthWithdrawalEvent(
            identifier=2,
            validator_index=validators[0].validator_index,  # type: ignore[arg-type]  # validator indexes are defined above and will not be None
            timestamp=TimestampMS(1611379127000),
            amount=FVal('0.01'),
            withdrawal_address=make_evm_address(),
            is_exit=False,
        ), EthBlockEvent(
            identifier=3,
            validator_index=validators[2].validator_index,  # type: ignore[arg-type]  # validator indexes are defined above and will not be None
            timestamp=TimestampMS(1671379127000),
            amount=ONE,
            fee_recipient=make_evm_address(),
            fee_recipient_tracked=True,
            block_number=42,
            is_mev_reward=True,
        )]
    with database.user_write() as cursor:
        dbevents.add_history_events(cursor, events)
        assert validators[0].validator_index is not None
        database.set_dynamic_cache(
            write_cursor=cursor,
            name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
            value=Timestamp(1739807677),
            index=validators[0].validator_index,
        )

    with database.conn.read_ctx() as cursor:  # assert events are in the DB
        assert events == dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validators': [validators[0].validator_index, validators[2].validator_index]},
    )
    assert_simple_ok_response(response)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validators': [validators[3].validator_index]},
    )
    assert_simple_ok_response(response)

    # after deleting validator indices, make sure their events are also gone
    with database.conn.read_ctx() as cursor:
        assert [events[0]] == dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )
        # Also confirm that the associated cached timestamp is removed
        assert database.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS,
            index=validators[0].validator_index,
        ) is None

    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'entries': [validators[1].serialize()], 'entries_limit': expected_limit, 'entries_found': 1}  # noqa: E501

    # Try to add validator with a custom ownership percentage
    custom_percentage_validators = [ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1606824023),
        validator_index=5235,
        public_key=Eth2PubKey('0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb'),
        withdrawal_address=string_to_evm_address('0x347A70cb4Ff0297102DC549B044c41bD61e22718'),
        ownership_proportion=FVal(0.4025),
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    ), ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1609038167),
        validator_index=43948,
        public_key=Eth2PubKey('0x922127b0722e0fca3ceeffe78a6d2f91f5b78edff42b65cce438f5430e67f389ff9f8f6a14a26ee6467051ddb1cc21eb'),
        withdrawal_address=string_to_evm_address('0xfA7F89a14d005F057107755cA18345728E2E3938'),
        ownership_proportion=FVal(0.5),
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    )]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={
            'validator_index': custom_percentage_validators[1].validator_index,
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
    result = assert_proper_sync_response_with_result(response)
    assert result == {'entries': [validator.serialize() for validator in custom_percentage_validators], 'entries_limit': expected_limit, 'entries_found': 2}  # noqa: E501


@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
def test_add_delete_validator_errors(
        rotkehlchen_api_server: 'APIServer',
        method: Literal['PUT', 'DELETE'],
) -> None:
    """Tests the error cases of adding/deleting a validator"""
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={},
    )
    if method == 'PUT':
        msg = 'Need to provide either a validator index or a public key for an eth2 validator'
    else:
        msg = 'Missing data for required field.'

    assert_error_response(
        response=response,
        contained_in_msg=msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    response = requests.request(
        method=method,
        url=api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validators': [-1]} if method == 'DELETE' else {'validator_index': -1},
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
        ), json={'validators': [999957426]} if method == 'DELETE' else {'validator_index': 999957426},  # noqa: E501
    )
    if method == 'PUT':
        msg = 'Validator data for 999957426 could not be found. Likely invalid validator'
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
            contained_in_msg='The given eth2 public key fooboosoozloklkl is not valid hex',
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


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    match_on=['beaconchain_matcher'],
)
@pytest.mark.freeze_time('2024-02-04 00:00:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('query_all_balances', [False, True])
def test_query_eth2_balances(
        rotkehlchen_api_server: 'APIServer',
        query_all_balances: bool,
) -> None:
    ownership_proportion = FVal(0.45)
    base_amount = FVal(32)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'entries': [], 'entries_limit': -1, 'entries_found': 0}

    validators = [ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1606824023),
        validator_index=5234,
        public_key=Eth2PubKey('0xb0456681ca4dc1a1276a9cab5915af9f9210f0eb104b4bd60164f59243b6159c3f3dab0d712cbae1360c7eb07af6a276'),
        withdrawal_address=string_to_evm_address('0x5675801e9346eA8165e7Eb80dcCD01dCa65c0f3A'),
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    ), ValidatorDetailsWithStatus(
        activation_timestamp=Timestamp(1606824023),
        validator_index=5235,
        public_key=Eth2PubKey('0x827e0f30c3d34e3ee58957dd7956b0f194d64cc404fca4a7313dc1b25ac1f28dcaddf59d05fbda798fa5b894c91b84fb'),
        withdrawal_address=string_to_evm_address('0x347A70cb4Ff0297102DC549B044c41bD61e22718'),
        ownership_proportion=ownership_proportion,
        status=ValidatorStatus.ACTIVE,
        validator_type=ValidatorType.DISTRIBUTING,
    )]
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': validators[0].validator_index},
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
    result = assert_proper_sync_response_with_result(response)
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

    outcome = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
        timeout=ASYNC_TASK_WAIT_TIMEOUT * 5,
    )

    assert len(outcome['per_account']) == 1  # only ETH2
    per_acc = outcome['per_account']['eth2']
    assert len(per_acc) == 2
    # hope they don't get slashed ;(
    amount_proportion = base_amount * ownership_proportion
    assert FVal(per_acc[validators[0].public_key]['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= base_amount  # noqa: E501
    assert FVal(per_acc[validators[1].public_key]['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= amount_proportion  # noqa: E501
    totals = outcome['totals']
    assert len(totals['assets']) == 1
    assert len(totals['liabilities']) == 0
    assert FVal(totals['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= base_amount + amount_proportion  # noqa: E501

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
    outcome = assert_proper_sync_response_with_result(response)

    assert len(outcome['per_account']) == 1  # only ETH2
    per_acc = outcome['per_account']['eth2']
    assert len(per_acc) == 3
    amount_proportion = base_amount * ownership_proportion
    assert FVal(per_acc[v0_pubkey]['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= base_amount  # noqa: E501
    assert FVal(per_acc[validators[0].public_key]['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= base_amount  # noqa: E501
    assert FVal(per_acc[validators[1].public_key]['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= amount_proportion  # noqa: E501
    totals = outcome['totals']
    assert len(totals['assets']) == 1
    assert len(totals['liabilities']) == 0
    assert FVal(totals['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= 2 * base_amount + amount_proportion  # noqa: E501


@pytest.mark.vcr(match_on=['beaconchain_matcher'])
@pytest.mark.freeze_time('2024-09-13 00:00:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_query_eth2_balances_without_premium(
        rotkehlchen_api_server: 'APIServer',
        eth2: 'Eth2',
) -> None:
    """Check that without premium the number of validators queried for balances
    is limited to FREE_VALIDATORS_LIMIT.
    """
    dbeth2 = DBEth2(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    for i in range(FREE_VALIDATORS_LIMIT + 1):
        result = eth2.beacon_inquirer.get_validator_data(indices_or_pubkeys=[i])
        result[0].ownership_proportion = FVal(0.25)
        with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            dbeth2.add_or_update_validators(write_cursor, [result[0]])

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainbalancesresource',
    ))
    balances_result = assert_proper_sync_response_with_result(response)
    assert len(balances_result['per_account']['eth2']) == FREE_VALIDATORS_LIMIT


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
    tx_hash, block_number, mev_reward, mevbot_address = deserialize_evm_tx_hash('0x8d0969db1e536969ba2e29abf8e8945e4304d49ae14523b66cbe9be5d52df804'), 15824493, '0.126458404824519798', string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990')  # noqa: E501

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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == result['entries_found'] == 7
    assert result['entries_total'] == 21
    event_identifier = None
    for entry in result['entries']:
        entry_block_number = entry['entry']['event_identifier'][4:]
        if entry_block_number == str(block_number):
            assert entry['grouped_events_num'] == 3
            event_identifier = entry['entry']['event_identifier']
        elif entry_block_number in {17055026, 16589592, 15938405}:
            assert entry['grouped_events_num'] == 2
        elif entry_block_number in {16135531, 15849710, 15798693}:
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == result['entries_found'] == 3
    assert result['entries_total'] == 34
    for outer_entry in result['entries']:
        entry = outer_entry['entry']
        if entry['sequence_index'] == 0:
            assert entry['identifier'] == 32
            assert entry['event_identifier'] == event_identifier
            assert entry['entry_type'] == 'eth block event'
            assert entry['event_type'] == 'informational'  # fee recipient not tracked
            assert entry['event_subtype'] == 'block production'
            assert entry['validator_index'] == vindex1
            assert entry['amount'] == '0.126419309459217215'
        elif entry['sequence_index'] == 1:
            assert entry['identifier'] == 33
            assert entry['event_identifier'] == event_identifier
            assert entry['entry_type'] == 'eth block event'
            assert entry['event_type'] == 'informational'
            assert entry['event_subtype'] == 'mev reward'
            assert entry['validator_index'] == vindex1
            assert entry['amount'] == mev_reward
        elif entry['sequence_index'] == 2:
            assert entry['identifier'] == 1
            assert entry['event_identifier'] == event_identifier
            assert entry['entry_type'] == 'evm event'
            assert entry['amount'] == mev_reward
            assert entry['tx_hash'] == tx_hash.hex()  # pylint: disable=no-member
            assert entry['user_notes'] == f'Receive {mev_reward} ETH from {mevbot_address} as mev reward for block {block_number} in {tx_hash.hex()}'  # pylint: disable=no-member  # noqa: E501
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
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
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 1
    for outer_entry in result['entries']:
        entry = outer_entry['entry']
        assert entry['entry_type'] != 'eth block event'


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    match_on=['beaconchain_matcher'],
)
@pytest.mark.freeze_time('2024-02-11 15:06:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('ethereum_accounts', [[
    CLEAN_HISTORY_WITHDRAWAL1, CLEAN_HISTORY_WITHDRAWAL2, CLEAN_HISTORY_WITHDRAWAL3,
]])
def test_get_validators(rotkehlchen_api_server: 'APIServer') -> None:
    """Test getting validators works for all filters"""
    _prepare_clean_validators(rotkehlchen_api_server)
    # Check they are returned fine
    validator1_data = {
        'activation_timestamp': 1704906839,
        'index': CLEAN_HISTORY_VALIDATOR1,
        'public_key': '0xb324c5869db5a524f9c3e2f3b82a786e7baa6ea150dc8f5c86a5342e6a7a5b4719ee1749c2f79e9e49d18a00f006118b',  # noqa: E501
        'status': 'active',
        'validator_type': 'distributing',
        'withdrawal_address': CLEAN_HISTORY_WITHDRAWAL1,
    }
    validator2_data = {
        'activation_timestamp': 1704906839,
        'index': CLEAN_HISTORY_VALIDATOR2,
        'public_key': '0x874df4549e48da22326e3f5c59a2e4e2096861236c8fd9314068f9e142812c216d440ed022371cdc5c3fcc2afac11693',  # noqa: E501
        'status': 'active',
        'validator_type': 'distributing',
        'withdrawal_address': CLEAN_HISTORY_WITHDRAWAL2,
    }
    validator3_data = {
        'activation_timestamp': 1680814295,
        'index': CLEAN_HISTORY_VALIDATOR3,
        'public_key': '0xa5de79a98e323f28de94fec045407324bbcd19bfddfe84b1cbc64df0f7bc77886f13c5bb639b2441238d2cd9c2b501d5',  # noqa: E501
        'status': 'exited',
        'validator_type': 'distributing',
        'withdrawal_address': CLEAN_HISTORY_WITHDRAWAL3,
        'withdrawable_timestamp': 1706912087,
    }
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [validator1_data, validator2_data, validator3_data]

    response = requests.get(  # Check filtering by index works
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_indices': [CLEAN_HISTORY_VALIDATOR1]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [validator1_data]

    response = requests.get(  # Check filtering by address works
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'addresses': [CLEAN_HISTORY_WITHDRAWAL2]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [validator2_data]

    response = requests.get(  # Check filtering by status works
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'status': 'exited'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'] == [validator3_data]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_balances_get_deleted_when_removing_validator(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that removing a validator correctly resets the balance caches"""
    response = requests.put(  # add a validator
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 10000},
    )
    assert_proper_sync_response_with_result(response)

    response = requests.get(api_url_for(  # query eth2 balances
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain='ETH2',
    ), json={'async_query': False})
    result = assert_proper_sync_response_with_result(response)
    assert FVal(result['totals']['assets']['ETH2'][DEFAULT_BALANCE_LABEL]['amount']) >= FVal(32)

    response = requests.delete(  # delete validator
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validators': [10000]},
    )
    assert_simple_ok_response(response)

    response = requests.get(api_url_for(  # query balances again
        rotkehlchen_api_server,
        'named_blockchain_balances_resource',
        blockchain='ETH2',
    ), json={'async_query': False})
    result = assert_proper_sync_response_with_result(response)
    assert len(result['totals']['assets']) == 0  # no assets in balances


@pytest.mark.vcr(match_on=['beaconchain_matcher'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_balances_of_exited_validators_are_not_queried(rotkehlchen_api_server: 'APIServer') -> None:  # noqa: E501
    """Test that the balances of exited validators are not queried at all."""
    response = requests.put(  # add an exited validator
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': CLEAN_HISTORY_VALIDATOR3},
    )
    assert_proper_sync_response_with_result(response)

    with patch('rotkehlchen.chain.ethereum.modules.eth2.beacon.BeaconInquirer.get_balances') as get_balances:  # noqa: E501
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'blockchainbalancesresource',
        ))
        result = assert_proper_sync_response_with_result(response)
        assert get_balances.call_count == 0
        assert result['per_account'] == {}
        assert result['totals'] == {'assets': {}, 'liabilities': {}}


@pytest.mark.vcr(match_on=['beaconchain_matcher'], filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
@pytest.mark.parametrize('ethereum_accounts', [['0xa966b01E2136953DF4F4914CfA9D37724E99a187']])
def test_consolidated_validators_status(rotkehlchen_api_server: 'APIServer') -> None:
    get_decoded_events_of_transaction(
        evm_inquirer=rotkehlchen_api_server.rest_api.rotkehlchen.chains_aggregator.ethereum.node_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x6e1dcb3172dbeea0434c3ebebfe231b4919d6cbe559cbe14a19ad25a21c490d9'),
    )
    response = requests.put(  # add a consolidated validator
        api_url_for(
            rotkehlchen_api_server,
            'eth2validatorsresource',
        ), json={'validator_index': 765882},
    )
    assert_proper_sync_response_with_result(response)

    # https://pectrified.com/mainnet/validator/765882
    response = requests.get(api_url_for(rotkehlchen_api_server, 'eth2validatorsresource'))
    result = assert_proper_sync_response_with_result(response)
    assert result['entries'][0]['index'] == 765882
    assert result['entries'][0]['status'] == 'consolidated'
    assert result['entries'][0]['consolidated_into'] == 765881
    assert result['entries'][0]['validator_type'] == 'distributing'


def test_redecode_block_production_events(rotkehlchen_api_server: 'APIServer') -> None:
    """Test redecoding of block production events.
    Events:
    - Three events to test combining block events with tx events.
        1. block event with an address that will not be tracked - Event type will not get updated.
        2. mev reward event - Should remain unmodified.
        3. evm event - Should be updated by combine_block_with_tx_events.
    - Two block events with an address that will get tracked:
        1. event_identifier will be passed when redecoding - Event type will be updated to staking.
        2. event_identifier will not be passed - Event type will remain informational.

    `fee_recipient_tracked` is initially set to False on all events.
    """
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    dbevents, dbevmtx = DBHistoryEvents(db), DBEvmTx(db)
    with db.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(write_cursor, [
            EthBlockEvent(
                validator_index=(v_index := 12345),
                timestamp=(timestamp := TimestampMS(1737836284)),
                amount=FVal(reward1 := '0.126419309459217215'),
                fee_recipient=(mev_builder_address := make_evm_address()),
                fee_recipient_tracked=False,
                block_number=(block_number := 1234567),
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=v_index,
                timestamp=timestamp,
                amount=FVal(reward2 := '0.126458404824519798'),
                fee_recipient=(fee_recipient_address := make_evm_address()),
                fee_recipient_tracked=False,
                block_number=block_number,
                is_mev_reward=True,
            ), EvmEvent(
                tx_hash=(tx_hash := deserialize_evm_tx_hash(tx_hash_str := '0x8d0969db1e536969ba2e29abf8e8945e4304d49ae14523b66cbe9be5d52df804')),  # noqa: E501
                sequence_index=0,
                timestamp=timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal(reward2),
                location_label=fee_recipient_address,
                notes=f'Received {reward2} ETH from {mev_builder_address}',
            ), EthBlockEvent(
                validator_index=v_index,
                timestamp=TimestampMS(timestamp + 1),
                amount=FVal(reward3 := '0.2'),
                fee_recipient=fee_recipient_address,
                fee_recipient_tracked=False,
                block_number=block_number + 1,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=v_index,
                timestamp=TimestampMS(timestamp + 2),
                amount=FVal(reward4 := '0.3'),
                fee_recipient=fee_recipient_address,
                fee_recipient_tracked=False,
                block_number=block_number + 2,
                is_mev_reward=False,
            ),
        ])
        dbevmtx.add_evm_transactions(  # transaction is needed for combine_block_with_tx_events
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=ts_ms_to_sec(timestamp),
                block_number=block_number,
                from_address=mev_builder_address,
                to_address=fee_recipient_address,
                value=126458404824519798,
                gas=27500,
                gas_price=9213569214,
                gas_used=0,  # irrelevant
                input_data=b'',  # irrelevant
                nonce=16239,
            )],
            relevant_address=fee_recipient_address,
        )
        db.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=fee_recipient_address,
            )],
        )

    assert_proper_response_with_result(
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'eth2stakingeventsresource'),
            json={'block_numbers': [block_number, block_number + 1], 'async_query': True},
        ),
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=True,
    )

    with db.conn.read_ctx() as cursor:
        # Check raw data from the db since deserializing EthBlockEvents performs the same check
        # for if the address is tracked that we are trying to test here.
        assert cursor.execute('SELECT * FROM history_events').fetchall() == [
            (1, 4, f'BP1_{block_number}', 0, timestamp, 'f', mev_builder_address, 'ETH', reward1, f'Validator {v_index} produced block {block_number} with {reward1} ETH going to {mev_builder_address} as the block reward', 'informational', 'block production', None, 0),  # noqa: E501
            (2, 4, f'BP1_{block_number}', 1, timestamp, 'f', fee_recipient_address, 'ETH', reward2, f'Validator {v_index} produced block {block_number}. Relayer reported {reward2} ETH as the MEV reward going to {fee_recipient_address}', 'informational', 'mev reward', None, 0),  # noqa: E501
            (3, 2, f'BP1_{block_number}', 2, timestamp, 'f', fee_recipient_address, 'ETH', reward2, f'Received {reward2} ETH from {mev_builder_address} as mev reward for block {block_number} in {tx_hash_str}', 'staking', 'mev reward', f'{{"validator_index": {v_index}}}', 0),  # noqa: E501
            (4, 4, f'BP1_{block_number + 1}', 0, timestamp + 1, 'f', fee_recipient_address, 'ETH', reward3, f'Validator {v_index} produced block {block_number + 1} with {reward3} ETH going to {fee_recipient_address} as the block reward', 'staking', 'block production', None, 0),  # noqa: E501
            (5, 4, f'BP1_{block_number + 2}', 0, timestamp + 2, 'f', fee_recipient_address, 'ETH', reward4, f'Validator {v_index} produced block {block_number + 2} with {reward4} ETH going to {fee_recipient_address} as the block reward', 'informational', 'block production', None, 0),  # noqa: E501
        ]
        # Confirm combine_block_with_tx_events marked the EthBlockEvent as hidden
        assert dbevents.get_hidden_event_ids(cursor) == [2]

    assert_error_response(  # Check validation with non-existent block number.
        response=requests.put(
            api_url_for(rotkehlchen_api_server, 'eth2stakingeventsresource'),
            json={'block_numbers': [block_number + 5], 'async_query': False},
        ),
        contained_in_msg='Some of the specified block numbers do not exist in the db',
        status_code=HTTPStatus.BAD_REQUEST,
    )
