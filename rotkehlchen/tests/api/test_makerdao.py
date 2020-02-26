from dataclasses import dataclass
from http import HTTPStatus
from typing import Dict, NamedTuple
from unittest.mock import _patch, patch

import pytest
import requests

from rotkehlchen.constants.ethereum import (
    MAKERDAO_POT_ADDRESS,
    MAKERDAO_PROXY_REGISTRY_ADDRESS,
    MAKERDAO_VAT_ADDRESS,
)
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.makerdao import _dsrdai_to_dai
from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ChecksumEthAddress

TEST_LATEST_BLOCKNUMBER = 9540749
TEST_LATEST_BLOCKNUMBER_HEX = hex(TEST_LATEST_BLOCKNUMBER)


def int_to_32byteshexstr(value: int) -> str:
    return '0x' + value.to_bytes(32, byteorder='big').hex()


def address_to_32byteshexstr(address: ChecksumEthAddress) -> str:
    return '0x' + '0' * 24 + address[2:].lower()


class DSRTestSetup(NamedTuple):
    etherscan_patch: _patch
    dsr_balance_response: Dict[ChecksumEthAddress, str]
    dsr_history_response: Dict[ChecksumEthAddress, Dict]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMockParameters():
    current_chi: int
    account1_current_normalized_balance: int
    account2_current_normalized_balance: int
    account1_join1_chi: int
    account1_join2_chi: int
    account1_exit1_chi: int
    account2_join1_chi: int
    account1_join1_normalized_balance: int
    account1_join2_normalized_balance: int
    account1_exit1_normalized_balance: int
    account2_join1_normalized_balance: int
    account1_join1_blocknumber: int
    account1_join2_blocknumber: int
    account1_exit1_blocknumber: int
    account2_join1_blocknumber: int


def blocknumber_to_timestamp(num: int) -> int:
    """Function to create a test timestamp for a test block number"""
    return num * 100 + 50


def mock_etherscan_for_dsr(
        etherscan: Etherscan,
        account1: ChecksumEthAddress,
        account2: ChecksumEthAddress,
        original_requests_get,
        params: DSRMockParameters,
) -> _patch:

    proxy1 = make_ethereum_address()
    proxy2 = make_ethereum_address()
    account1_join1_event = f"""{{"address": "{MAKERDAO_POT_ADDRESS}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_join1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0xwedontcare", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join1_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontacre", "transactionIndex": "0x79"}}"""  # noqa: E501

    account1_join1_deposit = params.account1_join1_normalized_balance * params.account1_join1_chi
    account1_join1_move_event = f"""{{"address": "{MAKERDAO_VAT_ADDRESS}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{MAKERDAO_POT_ADDRESS}", "{int_to_32byteshexstr(account1_join1_deposit)}"], "data": "0xwedontcare", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join1_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontcare", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_join2_event = f"""{{"address": "{MAKERDAO_POT_ADDRESS}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_join2_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0xwedontcare", "blockNumber": "{hex(params.account1_join2_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join2_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontacre", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_join2_deposit = params.account1_join2_normalized_balance * params.account1_join2_chi
    account1_join2_move_event = f"""{{"address": "{MAKERDAO_VAT_ADDRESS}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{MAKERDAO_POT_ADDRESS}", "{int_to_32byteshexstr(account1_join2_deposit)}"], "data": "0xwedontcare", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join2_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontcare", "transactionIndex": "0x79"}}"""  # noqa: E501

    account1_exit1_event = f"""{{"address": "{MAKERDAO_POT_ADDRESS}", "topics": ["0x7f8661a100000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_exit1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0xwedontcare", "blockNumber": "{hex(params.account1_exit1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_exit1_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontacre", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_exit1_withdrawal = (
        params.account1_exit1_normalized_balance * params.account1_exit1_chi
    )
    account1_exit1_move_event = f"""{{"address": "{MAKERDAO_VAT_ADDRESS}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{MAKERDAO_POT_ADDRESS}", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(account1_exit1_withdrawal)}"], "data": "0xwedontcare", "blockNumber": "{hex(params.account1_exit1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_exit1_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontcare", "transactionIndex": "0x79"}}"""  # noqa: E501
    account2_join1_event = f"""{{"address": "{MAKERDAO_POT_ADDRESS}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy2)}", "{int_to_32byteshexstr(params.account2_join1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0xwedontcare", "blockNumber": "{hex(params.account2_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account2_join1_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontacre", "transactionIndex": "0x79"}}"""  # noqa: E501

    account2_join1_deposit = params.account2_join1_normalized_balance * params.account2_join1_chi
    account2_join1_move_event = f"""{{"address": "{MAKERDAO_VAT_ADDRESS}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy2)}", "{MAKERDAO_POT_ADDRESS}", "{int_to_32byteshexstr(account2_join1_deposit)}"], "data": "0xwedontcare", "blockNumber": "{hex(params.account2_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account2_join1_blocknumber))}", "gasPrice": "dontcare", "gasUsed": "dontcare", "logIndex": "0x6c", "transactionHash": "dontcare", "transactionIndex": "0x79"}}"""  # noqa: E501

    def mock_requests_get(url, *args, **kwargs):
        if 'etherscan.io/api?module=proxy&action=eth_blockNumber' in url:
            response = f'{{"status":"1","message":"OK","result":"{TEST_LATEST_BLOCKNUMBER_HEX}"}}'

        elif 'etherscan.io/api?module=proxy&action=eth_call' in url:
            to_address = url.split(
                'https://api.etherscan.io/api?module=proxy&action=eth_call&to=',
            )[1][:42]
            input_data = url.split('data=')[1].split('&apikey')[0]
            if to_address == MAKERDAO_PROXY_REGISTRY_ADDRESS:
                if not input_data.startswith('0xc4552791'):
                    raise AssertionError(
                        'Call to unexpected method of DSR ProxyRegistry during tests',
                    )

                # It's a call to proxy registry. Return the mapping
                if account1[2:].lower() in input_data:
                    proxy_account = address_to_32byteshexstr(proxy1)
                elif account2[2:].lower() in input_data:
                    proxy_account = address_to_32byteshexstr(proxy2)
                else:
                    proxy_account = '0x' + '0' * 64
                response = f'{{"status":"1","message":"OK","result":"{proxy_account}"}}'
            elif to_address == MAKERDAO_POT_ADDRESS:
                if input_data.startswith('0x0bebac86'):  # pie
                    if proxy1[2:].lower() in input_data:
                        result = int_to_32byteshexstr(params.account1_normalized_balance)
                    elif proxy2[2:].lower() in input_data:
                        result = int_to_32byteshexstr(params.account2_normalized_balance)
                    else:
                        # result = int_to_32byteshexstr(0)
                        raise AssertionError('Pie call for unexpected account during tests')
                elif input_data.startswith('0xc92aecc4'):  # chi
                    result = int_to_32byteshexstr(params.current_chi)
                else:
                    raise AssertionError(
                        'Call to unexpected method of MakerDAO pot during tests',
                    )

                response = f'{{"status":"1","message":"OK","result":"{result}"}}'

            else:
                raise AssertionError(
                    f'Etherscan call to unknown contract {to_address} during tests',
                )
        elif 'etherscan.io/api?module=logs&action=getLogs' in url:
            contract_address = url.split('&address=')[1].split('&topic0')[0]
            topic0 = url.split('&topic0=')[1].split('&topic0_1')[0]
            topic1 = url.split('&topic1=')[1].split('&topic1_2')[0]
            topic2 = None
            if '&topic2=' in url:
                topic2 = url.split('&topic2=')[1].split('&')[0]
            from_block = int(url.split('&fromBlock=')[1].split('&')[0])
            to_block = int(url.split('&toBlock=')[1].split('&')[0])

            if contract_address == MAKERDAO_POT_ADDRESS:
                if topic0.startswith('0x049878f3'):  # join

                    events = []
                    if proxy1[2:].lower() in topic1:
                        if from_block <= params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_event)
                        if from_block <= params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_event)
                    elif proxy2[2:].lower() in topic1:
                        if from_block <= params.account2_join1_blocknumber <= to_block:
                            events.append(account2_join1_event)
                    else:
                        raise AssertionError(
                            f'Etherscan log query to makerdao POT contract for '
                            f'join for unknown account {topic1}',
                        )
                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'

                elif topic0.startswith('0x7f8661a1'):  # exit
                    events = []
                    if proxy1[2:].lower() in topic1:
                        if from_block <= params.account1_exit1_blocknumber <= to_block:
                            events.append(account1_exit1_event)

                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'
                else:
                    raise AssertionError('Etherscan unknown log query to makerdao POT contract')

            elif contract_address == MAKERDAO_VAT_ADDRESS:
                if topic0.startswith('0xbb35783b'):  # move
                    events = []
                    if proxy1[2:].lower() in topic1:  # deposit from acc1
                        if from_block <= params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_move_event)
                        if from_block <= params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_move_event)
                    elif proxy2[2:].lower() in topic1:  # deposit from acc2
                        if from_block <= params.account2_join1_blocknumber <= to_block:
                            events.append(account2_join1_move_event)
                    elif proxy1[2:].lower() in topic2:  # withdrawal from acc1

                        if from_block <= params.account1_exit1_blocknumber <= to_block:
                            events.append(account1_exit1_move_event)

                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'
                else:
                    raise AssertionError('Etherscan unknown log query to makerdao VAT contract')
            else:
                raise AssertionError(
                    f'Etherscan getLogs call to unknown contract {contract_address} during tests',
                )
        else:
            return original_requests_get(url, *args, **kwargs)

        return MockResponse(200, response)

    return patch.object(etherscan.session, 'get', wraps=mock_requests_get)


def setup_tests_for_dsr(
        etherscan: Etherscan,
        account1: ChecksumEthAddress,
        account2: ChecksumEthAddress,
        original_requests_get,
) -> DSRTestSetup:

    current_chi = 1123323222211111111111001249911111
    chi_distance = 1010020050000000000050000000000
    params = DSRMockParameters(
        account1_current_normalized_balance=123232334324234324,
        account2_current_normalized_balance=5323213213123534234,
        current_chi=current_chi,
        account1_join1_normalized_balance=1321333211111121,
        account1_join2_normalized_balance=421333211111121,
        account1_exit1_normalized_balance=221333211131121,
        account2_join1_normalized_balance=1621333211111121,
        account1_join1_chi=current_chi - 4 * chi_distance,
        account1_join2_chi=current_chi - 3 * chi_distance,
        account1_exit1_chi=current_chi - 2 * chi_distance,
        account2_join1_chi=current_chi - 2 * chi_distance,
        account1_join1_blocknumber=9000100,
        account1_join2_blocknumber=9102100,
        account1_exit1_blocknumber=9232100,
        account2_join1_blocknumber=9342100,
    )
    etherscan_patch = mock_etherscan_for_dsr(
        etherscan=etherscan,
        account1=account1,
        account2=account2,
        original_requests_get=original_requests_get,
        params=params,
    )

    dsr_balance_response = {
        account1: _dsrdai_to_dai(params.account1_current_normalized_balance * current_chi),
        account2: _dsrdai_to_dai(params.account2_current_normalized_balance * current_chi),
    }
    account1_deposit1 = params.account1_join1_normalized_balance * params.account1_join1_chi
    account1_deposit2 = params.account1_join2_normalized_balance * params.account1_join2_chi
    account1_withdrawal1 = params.account1_exit1_normalized_balance * params.account1_exit1_chi
    account2_deposit1 = params.account2_join1_normalized_balance * params.account2_join1_chi
    account1_gain_so_far = (
        params.account1_join1_normalized_balance +
        params.account1_join2_normalized_balance -
        params.account1_exit1_normalized_balance
    ) * current_chi - account1_deposit1 - account1_deposit2 + account1_withdrawal1
    account2_gain_so_far = (
        params.account2_join1_normalized_balance * current_chi - account2_deposit1
    )
    dsr_history_response = {
        account1: {
            'gain_so_far': _dsrdai_to_dai(account1_gain_so_far),
            'movements': [{
                'movement_type': 'deposit',
                'gain_so_far': '0.0',
                'amount': _dsrdai_to_dai(account1_deposit1),
                'block_number': params.account1_join1_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account1_join1_blocknumber),
            }, {
                'movement_type': 'deposit',
                'gain_so_far': _dsrdai_to_dai(
                    params.account1_join1_normalized_balance * params.account1_join2_chi -
                    account1_deposit1
                ),
                'amount': _dsrdai_to_dai(account1_deposit2),
                'block_number': params.account1_join2_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account1_join2_blocknumber),
            }, {
                'movement_type': 'withdrawal',
                'gain_so_far': _dsrdai_to_dai(
                    (
                        params.account1_join1_normalized_balance +
                        params.account1_join2_normalized_balance
                    ) * params.account1_exit1_chi -
                    (account1_deposit1 + account1_deposit2),
                ),
                'amount': _dsrdai_to_dai(account1_withdrawal1),
                'block_number': params.account1_exit1_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account1_exit1_blocknumber),
            }],
        },
        account2: {
            'gain_so_far': _dsrdai_to_dai(account2_gain_so_far),
            'movements': [{
                'movement_type': 'deposit',
                'gain_so_far': '0.0',
                'amount': _dsrdai_to_dai(account2_deposit1),
                'block_number': params.account2_join1_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account2_join1_blocknumber),
            }],
        },
    }
    return DSRTestSetup(
        etherscan_patch=etherscan_patch,
        dsr_balance_response=dsr_balance_response,
        dsr_history_response=dsr_history_response,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
def test_query_current_dsr_balance(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    account1 = ethereum_accounts[0]
    account2 = ethereum_accounts[2]
    setup = setup_tests_for_dsr(
        etherscan=rotki.etherscan,
        account1=account1,
        account2=account2,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "makerdaodsrbalanceresource",
        ))

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert len(result) == 2

    assert FVal(result[account1]) == setup.dsr_balance_response[account1]
    assert FVal(result[account2]) == setup.dsr_balance_response[account2]


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
def test_query_historical_dsr_non_premium(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    account1 = ethereum_accounts[0]
    account2 = ethereum_accounts[2]
    setup = setup_tests_for_dsr(
        etherscan=rotki.etherscan,
        account1=account1,
        account2=account2,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "makerdaodsrhistoryresource",
        ))

    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_historical_dsr(
        rotkehlchen_api_server,
        ethereum_accounts,
        number_of_eth_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    account1 = ethereum_accounts[0]
    account2 = ethereum_accounts[2]
    setup = setup_tests_for_dsr(
        etherscan=rotki.etherscan,
        account1=account1,
        account2=account2,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "makerdaodsrhistoryresource",
        ))

    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result']
    assert len(result) == 2
    for account, entry in setup.dsr_history_response.items():
        assert len(entry) == len(result[account])
        for key, val in entry.items():
            if key == 'movements':
                assert len(val) == len(result[account]['movements'])
                for idx, movement in enumerate(val):
                    for mov_key, mov_val in movement.items():
                        if mov_key == 'movement_type':
                            assert mov_val == result[account]['movements'][idx][mov_key]
                        else:
                            assert FVal(mov_val) == FVal(
                                result[account]['movements'][idx][mov_key]
                            )

            else:
                assert FVal(result[account][key]) == FVal(val)
