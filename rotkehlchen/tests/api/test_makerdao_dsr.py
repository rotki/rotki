import random
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Dict, List, NamedTuple
from unittest.mock import _patch, patch

import pytest
import requests
from web3 import Web3
from web3._utils.abi import get_abi_output_types

from rotkehlchen.chain.ethereum.modules.makerdao.dsr import _dsrdai_to_dai
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.ethereum import (
    DS_PROXY_REGISTRY,
    ETH_MULTICALL,
    MAKERDAO_DAI_JOIN,
    MAKERDAO_POT,
    MAKERDAO_VAT,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.makerdao import mock_proxies
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChecksumEvmAddress

mocked_prices = {
    'DAI': {
        'USD': {
            1582699808: FVal('1.002'),
            1584024065: FVal('1.002'),
            1585286480: FVal('1.023'),
            1585286769: FVal('1.023'),
            1585290263: FVal('1.023'),
            1586785858: FVal('1.024'),
            1586788927: FVal('1.024'),
            1586805054: FVal('1.024'),
            1587539880: FVal('1.016'),
            1587539889: FVal('1.016'),
            1587910979: FVal('1.015'),
            1588174425: FVal('1.014'),
            1588664698: FVal('1.006'),
            1588696496: FVal('1.006'),
            1588964616: FVal('1.006'),
            1589989097: FVal('1.003'),
            1590042891: FVal('1.001'),
            1590044118: FVal('1.001'),
            1590521879: FVal('1.003'),
        },
    },
}

TEST_LATEST_BLOCKNUMBER = 9540749
TEST_LATEST_BLOCKNUMBER_HEX = hex(TEST_LATEST_BLOCKNUMBER)


def int_to_32byteshexstr(value: int) -> str:
    return '0x' + value.to_bytes(32, byteorder='big').hex()


def address_to_32byteshexstr(address: ChecksumEvmAddress) -> str:
    return '0x' + '0' * 24 + address[2:].lower()


class DSRTestSetup(NamedTuple):
    etherscan_patch: _patch
    dsr_balance_response: Dict[str, Any]
    dsr_history_response: Dict[ChecksumEvmAddress, Dict[str, Any]]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMockParameters():
    current_dsr: int
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
        account1: ChecksumEvmAddress,
        account2: ChecksumEvmAddress,
        account3: ChecksumEvmAddress,
        original_requests_get,
        params: DSRMockParameters,
) -> _patch:

    proxy1 = make_ethereum_address()
    proxy2 = make_ethereum_address()
    targets = [address_to_32byteshexstr(proxy1), address_to_32byteshexstr(proxy2), '0x0000000000000000000000000000000000000000000000000000000000000000']  # noqa: E501

    sorted_accounts = sorted(zip([account1, account2, account3], targets), key=lambda x: x[0])
    proxies = [y[1] for y in sorted_accounts]

    account1_join1_event = f"""{{"address": "{MAKERDAO_POT.address}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_join1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    account1_join1_deposit = params.account1_join1_normalized_balance * params.account1_join1_chi
    account1_join1_move_event = f"""{{"address": "{MAKERDAO_VAT.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{MAKERDAO_POT.address}", "{int_to_32byteshexstr(account1_join1_deposit // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_join2_event = f"""{{"address": "{MAKERDAO_POT.address}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_join2_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account1_join2_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join2_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_join2_deposit = params.account1_join2_normalized_balance * params.account1_join2_chi
    account1_join2_move_event = f"""{{"address": "{MAKERDAO_VAT.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{MAKERDAO_POT.address}", "{int_to_32byteshexstr(account1_join2_deposit // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join2_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    account1_exit1_event = f"""{{"address": "{MAKERDAO_POT.address}", "topics": ["0x7f8661a100000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_exit1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account1_exit1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_exit1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_exit1_withdrawal = (
        params.account1_exit1_normalized_balance * params.account1_exit1_chi
    )
    account1_exit1_move_event = f"""{{"address": "{MAKERDAO_VAT.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{MAKERDAO_POT.address}", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(account1_exit1_withdrawal // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account1_exit1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_exit1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account2_join1_event = f"""{{"address": "{MAKERDAO_POT.address}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy2)}", "{int_to_32byteshexstr(params.account2_join1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account2_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account2_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    account2_join1_deposit = params.account2_join1_normalized_balance * params.account2_join1_chi
    account2_join1_move_event = f"""{{"address": "{MAKERDAO_VAT.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy2)}", "{MAKERDAO_POT.address}", "{int_to_32byteshexstr(account2_join1_deposit // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account2_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account2_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    # Not sure how to convince pylint that this ChecksumEvmAddress IS a subscriptable object
    proxy1_contents = proxy1[2:].lower()  # pylint: disable=unsubscriptable-object
    proxy2_contents = proxy2[2:].lower()  # pylint: disable=unsubscriptable-object

    def mock_requests_get(url, *args, **kwargs):
        if 'etherscan.io/api?module=proxy&action=eth_blockNumber' in url:
            response = f'{{"status":"1","message":"OK","result":"{TEST_LATEST_BLOCKNUMBER_HEX}"}}'
        elif 'etherscan.io/api?module=proxy&action=eth_call' in url:
            to_address = url.split(
                'https://api.etherscan.io/api?module=proxy&action=eth_call&to=',
            )[1][:42]
            input_data = url.split('data=')[1].split('&apikey')[0]
            if to_address == DS_PROXY_REGISTRY.address:
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
            elif to_address == ETH_MULTICALL.address:
                web3 = Web3()
                contract = web3.eth.contract(address=ETH_MULTICALL.address, abi=ETH_MULTICALL.abi)
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = contract.functions.abi[1]
                output_types = get_abi_output_types(fn_abi)
                args = [1, proxies]
                result = '0x' + web3.codec.encode_abi(output_types, args).hex()
                response = f'{{"status":"1","message":"OK","result":"{result}"}}'
            elif to_address == MAKERDAO_POT.address:
                if input_data.startswith('0x0bebac86'):  # pie
                    if proxy1_contents in input_data:
                        result = int_to_32byteshexstr(params.account1_current_normalized_balance)
                    elif proxy2_contents in input_data:
                        result = int_to_32byteshexstr(params.account2_current_normalized_balance)
                    else:
                        # result = int_to_32byteshexstr(0)
                        raise AssertionError('Pie call for unexpected account during tests')
                elif input_data.startswith('0xc92aecc4'):  # chi
                    result = int_to_32byteshexstr(params.current_chi)
                elif input_data.startswith('0x487bf082'):  # dsr
                    result = int_to_32byteshexstr(params.current_dsr)
                else:
                    raise AssertionError(
                        'Call to unexpected method of MakerDao pot during tests',
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

            if contract_address == MAKERDAO_POT.address:
                if topic0.startswith('0x049878f3'):  # join

                    events = []
                    if proxy1_contents in topic1:
                        if from_block <= params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_event)
                        if from_block <= params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_event)
                    elif proxy2_contents in topic1:
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
                    if proxy1_contents in topic1:
                        if from_block <= params.account1_exit1_blocknumber <= to_block:
                            events.append(account1_exit1_event)

                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'
                else:
                    raise AssertionError('Etherscan unknown log query to makerdao POT contract')

            elif contract_address == MAKERDAO_VAT.address:
                if topic0.startswith('0xbb35783b'):  # move
                    events = []
                    if proxy1_contents in topic1:  # deposit from acc1
                        if from_block <= params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_move_event)
                        if from_block <= params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_move_event)
                    elif proxy2_contents in topic1:  # deposit from acc2
                        if from_block <= params.account2_join1_blocknumber <= to_block:
                            events.append(account2_join1_move_event)
                    elif proxy1_contents in topic2:  # withdrawal from acc1

                        if from_block <= params.account1_exit1_blocknumber <= to_block:
                            events.append(account1_exit1_move_event)

                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'
                else:
                    raise AssertionError('Etherscan unknown log query to makerdao VAT contract')
            elif contract_address == MAKERDAO_DAI_JOIN.address:
                events = []
                if topic0.startswith('0x3b4da69f'):  # join
                    if proxy1_contents in topic1:  # deposit from acc1
                        if from_block <= params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_move_event)
                        if from_block <= params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_move_event)
                    elif proxy2_contents in topic1:  # deposit from acc2
                        if from_block <= params.account2_join1_blocknumber <= to_block:
                            events.append(account2_join1_move_event)
                elif topic0.startswith('0xef693bed'):  # exit
                    if from_block <= params.account1_exit1_blocknumber <= to_block:
                        events.append(account1_exit1_move_event)
                else:
                    raise AssertionError('Etherscan unknown call to makerdao DAIJOIN contract')
                response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'

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
        accounts: List[ChecksumEvmAddress],
        original_requests_get,
) -> DSRTestSetup:
    account1 = accounts[0]
    account2 = accounts[2]
    account3 = accounts[1]

    current_dsr = 1000000002440418608258400030
    current_chi = 1123323222211111111111001249911111
    chi_distance = 1010020050000000000050000000000
    params = DSRMockParameters(
        account1_current_normalized_balance=123232334324234324,
        account2_current_normalized_balance=5323213213123534234,
        current_chi=current_chi,
        current_dsr=current_dsr,
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
        account3=account3,
        original_requests_get=original_requests_get,
        params=params,
    )

    dsr_balance_response = {
        'current_dsr': '8.022774065220581075333120100',
        'balances': {
            account1: _dsrdai_to_dai(params.account1_current_normalized_balance * current_chi),
            account2: _dsrdai_to_dai(params.account2_current_normalized_balance * current_chi),
        },
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
            'gain_so_far': {
                'amount': _dsrdai_to_dai(account1_gain_so_far),
                'usd_value': _dsrdai_to_dai(account1_gain_so_far),
            },
            'movements': [{
                'movement_type': 'deposit',
                'gain_so_far': {
                    'amount': '0.0',
                    'usd_value': '0.0',
                },
                'value': {
                    'amount': _dsrdai_to_dai(account1_deposit1),
                    'usd_value': _dsrdai_to_dai(account1_deposit1),
                },
                'block_number': params.account1_join1_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account1_join1_blocknumber),
            }, {
                'movement_type': 'deposit',
                'gain_so_far': {
                    'amount': _dsrdai_to_dai(
                        params.account1_join1_normalized_balance * params.account1_join2_chi -
                        account1_deposit1,
                    ),
                    'usd_value': _dsrdai_to_dai(
                        params.account1_join1_normalized_balance * params.account1_join2_chi -
                        account1_deposit1,
                    ),
                },
                'value': {
                    'amount': _dsrdai_to_dai(account1_deposit2),
                    'usd_value': _dsrdai_to_dai(account1_deposit2),
                },
                'block_number': params.account1_join2_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account1_join2_blocknumber),
            }, {
                'movement_type': 'withdrawal',
                'gain_so_far': {
                    'amount': _dsrdai_to_dai(
                        (
                            params.account1_join1_normalized_balance +
                            params.account1_join2_normalized_balance
                        ) * params.account1_exit1_chi -
                        (account1_deposit1 + account1_deposit2),
                    ),
                    'usd_value': _dsrdai_to_dai(
                        (
                            params.account1_join1_normalized_balance +
                            params.account1_join2_normalized_balance
                        ) * params.account1_exit1_chi -
                        (account1_deposit1 + account1_deposit2),
                    ),
                },
                'value': {
                    'amount': _dsrdai_to_dai(account1_withdrawal1),
                    'usd_value': _dsrdai_to_dai(account1_withdrawal1),
                },
                'block_number': params.account1_exit1_blocknumber,
                'timestamp': blocknumber_to_timestamp(params.account1_exit1_blocknumber),
            }],
        },
        account2: {
            'gain_so_far': {
                'amount': _dsrdai_to_dai(account2_gain_so_far),
                'usd_value': _dsrdai_to_dai(account2_gain_so_far),
            },
            'movements': [{
                'movement_type': 'deposit',
                'gain_so_far': {
                    'amount': '0.0',
                    'usd_value': '0.0',
                },
                'value': {
                    'amount': _dsrdai_to_dai(account2_deposit1),
                    'usd_value': _dsrdai_to_dai(account2_deposit1),
                },
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


def assert_dsr_current_result_is_correct(result: Dict[str, Any], setup: DSRTestSetup) -> None:
    assert len(result) == len(setup.dsr_balance_response)
    for key, val in setup.dsr_balance_response.items():
        if key == 'balances':
            assert len(val) == len(result['balances'])
            for account, balance_val in setup.dsr_balance_response['balances'].items():
                assert FVal(balance_val) == FVal(result['balances'][account]['amount'])
                assert FVal(balance_val) == FVal(result['balances'][account]['usd_value'])
        else:
            assert FVal(val) == FVal(result[key])


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('mocked_current_prices', [{A_DAI: ONE}])
def test_query_current_dsr_balance(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_tests_for_dsr(
        etherscan=rotki.etherscan,
        accounts=ethereum_accounts,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "makerdaodsrbalanceresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)

    assert_dsr_current_result_is_correct(outcome, setup)


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_historical_dsr_non_premium(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_tests_for_dsr(
        etherscan=rotki.etherscan,
        accounts=ethereum_accounts,
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


def assert_dsr_history_result_is_correct(result: Dict[str, Any], setup: DSRTestSetup) -> None:
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
                        elif mov_key in ('gain_so_far', 'value'):
                            assert FVal(mov_val['amount']).is_close(FVal(
                                result[account]['movements'][idx][mov_key]['amount'],
                            ), max_diff='1e-8')
                            assert FVal(mov_val['usd_value']).is_close(FVal(
                                result[account]['movements'][idx][mov_key]['usd_value'],
                            ), max_diff='1e-8')
                        else:
                            assert FVal(mov_val).is_close(FVal(
                                result[account]['movements'][idx][mov_key],
                            ), max_diff='1e-8')
            elif key == 'gain_so_far':
                assert FVal(result[account][key]['amount']).is_close(FVal(val['amount']))
                assert FVal(result[account][key]['usd_value']).is_close(FVal(val['usd_value']))
            else:
                assert FVal(result[account][key]).is_close(FVal(val))


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('mocked_current_prices', [{A_DAI: ONE}])
def test_query_historical_dsr(
        rotkehlchen_api_server,
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
):
    """Test DSR history is correctly queried

    This (and the async version) is a very hard to maintain test due to mocking
    everything.

    TODO: Perhaps change it to querying etherscan/chain until a given block for a
    given DSR account and check that until then all data match.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_tests_for_dsr(
        etherscan=rotki.etherscan,
        accounts=ethereum_accounts,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "makerdaodsrhistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        else:
            outcome = assert_proper_response_with_result(response)

    assert_dsr_history_result_is_correct(outcome, setup)


@pytest.mark.parametrize('number_of_eth_accounts', [1])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('mocked_current_prices', [{A_DAI: ONE}])
def test_query_historical_dsr_with_a_zero_withdrawal(
        rotkehlchen_api_server,
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
):
    """Test DSR for an account that was opened while DSR is 0 and made a 0 DAI withdrawal

    Essentially reproduce DSR problem reported here: https://github.com/rotki/rotki/issues/1032

    The account in question operates in a zero DSR environment but the reported
    problem seems to be just because he tried a zero DAI withdrawal
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    original_get_logs = rotki.chains_aggregator.ethereum.get_logs
    proxies_mapping = {
        # proxy for 0x714696C5a872611F76655Bc163D0131cBAc60a70
        ethereum_accounts[0]: '0xAe9996b76bdAa003ace6D66328A6942565f5768d',
    }
    mock_proxies(rotki, proxies_mapping, 'makerdao_dsr')

    # Query only until a block we know DSR is 0 and we know the number
    # of DSR events
    def mock_get_logs(
            contract_address,
            abi,
            event_name,
            argument_filters,
            from_block,
            to_block='latest',  # pylint: disable=unused-argument
    ):
        return original_get_logs(
            contract_address,
            abi,
            event_name,
            argument_filters,
            from_block,
            to_block=10149816,  # A block at which DSR is still zero
        )

    patched_get_logs = patch.object(
        rotki.chains_aggregator.ethereum,
        'get_logs',
        side_effect=mock_get_logs,
    )

    with patched_get_logs:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "makerdaodsrhistoryresource",
        ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    result = json_data['result'][ethereum_accounts[0]]
    assert result['gain_so_far'] == {'amount': '0', 'usd_value': '0'}
    movements = result['movements']
    expected_movements = [{
        'movement_type': 'deposit',
        'gain_so_far': {
            'amount': ZERO,
            'usd_value': ZERO,
        },
        'value': {
            'amount': FVal('79'),
            'usd_value': FVal('79'),
        },
        'block_number': 9953028,
        'timestamp': 1587970286,
        'tx_hash': '0x988aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289',
    }, {
        'movement_type': 'withdrawal',
        'gain_so_far': {
            'amount': ZERO,
            'usd_value': ZERO,
        },
        'value': {
            'amount': FVal('79'),
            'usd_value': FVal('79'),
        },
        'block_number': 9968906,
        'timestamp': 1588182567,
        'tx_hash': '0x2a1bee69b9bafe031026dbcc8f199881b568fd767482b5436dd1cd94f2642443',
    }, {
        'movement_type': 'withdrawal',
        'gain_so_far': {
            'amount': ZERO,
            'usd_value': ZERO,
        },
        'value': {
            'amount': ZERO,
            'usd_value': ZERO,
        },
        'block_number': 9968906,
        'timestamp': 1588182567,
        'tx_hash': '0x618fc9542890a2f58ab20a3c12d173b3638af11fda813e61788e242b4fc9a756',
    }]
    assert_serialized_lists_equal(movements, expected_movements, max_diff="1e-26")
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0


@pytest.mark.parametrize('ethereum_accounts', [['0xf753beFE986e8Be8EBE7598C9d2b6297D9DD6662']])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_dsr_for_account_with_proxy_but_no_dsr(
        rotkehlchen_api_server,
):
    """Assure that an account with a DSR proxy but no DSR balance isn't returned in the balances"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaodsrbalanceresource",
    ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert len(json_data['result']['balances']) == 0
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "makerdaodsrhistoryresource",
    ))
    json_data = response.json()
    assert json_data['message'] == ''
    assert len(json_data['result']) == 0
