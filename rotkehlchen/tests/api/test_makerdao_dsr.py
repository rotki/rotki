import random
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, NamedTuple
from unittest.mock import _patch, patch

import pytest
import requests
from eth_typing.abi import ABI
from eth_utils.abi import get_abi_output_types
from web3 import Web3

from rotkehlchen.chain.ethereum.modules.makerdao.dsr import _dsrdai_to_dai
from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.blockchain import ETHERSCAN_API_URL
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

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

TEST_ADDRESS_1 = '0x9343efFF92BF74D5aFd3d0079D24cA65234bE4CD'


def int_to_32byteshexstr(value: int) -> str:
    return '0x' + value.to_bytes(32, byteorder='big').hex()


def address_to_32byteshexstr(address: ChecksumEvmAddress) -> str:
    return '0x' + '0' * 24 + address[2:].lower()


class DSRTestSetup(NamedTuple):
    etherscan_patch: _patch
    dsr_balance_response: dict[str, Any]
    dsr_history_response: dict[ChecksumEvmAddress, dict[str, Any]]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMockParameters:
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
        contracts: EvmContracts,
        account1: ChecksumEvmAddress,
        account2: ChecksumEvmAddress,
        original_requests_get: Callable,
        params: DSRMockParameters,
) -> _patch:
    ds_proxy_registry = contracts.contract(string_to_evm_address('0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4'))  # noqa: E501
    makerdao_dai_join = contracts.contract(string_to_evm_address('0x9759A6Ac90977b93B58547b4A71c78317f391A28'))  # noqa: E501
    makerdao_pot = contracts.contract(string_to_evm_address('0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7'))  # noqa: E501
    makerdao_vat = contracts.contract(string_to_evm_address('0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B'))  # noqa: E501
    eth_multicall = contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696'))  # noqa: E501

    proxy1 = make_evm_address()
    proxy2 = make_evm_address()
    proxies = [address_to_32byteshexstr(proxy1), address_to_32byteshexstr(proxy2), '0x0000000000000000000000000000000000000000000000000000000000000000']  # noqa: E501

    account1_join1_event = f"""{{"address": "{makerdao_pot.address}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_join1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    account1_join1_deposit = params.account1_join1_normalized_balance * params.account1_join1_chi
    account1_join1_move_event = f"""{{"address": "{makerdao_vat.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{makerdao_pot.address}", "{int_to_32byteshexstr(account1_join1_deposit // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_join2_event = f"""{{"address": "{makerdao_pot.address}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_join2_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account1_join2_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join2_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_join2_deposit = params.account1_join2_normalized_balance * params.account1_join2_chi
    account1_join2_move_event = f"""{{"address": "{makerdao_vat.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{makerdao_pot.address}", "{int_to_32byteshexstr(account1_join2_deposit // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account1_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_join2_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    account1_exit1_event = f"""{{"address": "{makerdao_pot.address}", "topics": ["0x7f8661a100000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(params.account1_exit1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account1_exit1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_exit1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account1_exit1_withdrawal = (
        params.account1_exit1_normalized_balance * params.account1_exit1_chi
    )
    account1_exit1_move_event = f"""{{"address": "{makerdao_vat.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{makerdao_pot.address}", "{address_to_32byteshexstr(proxy1)}", "{int_to_32byteshexstr(account1_exit1_withdrawal // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account1_exit1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account1_exit1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501
    account2_join1_event = f"""{{"address": "{makerdao_pot.address}", "topics": ["0x049878f300000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy2)}", "{int_to_32byteshexstr(params.account2_join1_normalized_balance)}", "0x0000000000000000000000000000000000000000000000000000000000000000"], "data": "0x1", "blockNumber": "{hex(params.account2_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account2_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    account2_join1_deposit = params.account2_join1_normalized_balance * params.account2_join1_chi
    account2_join1_move_event = f"""{{"address": "{makerdao_vat.address}", "topics": ["0xbb35783b00000000000000000000000000000000000000000000000000000000", "{address_to_32byteshexstr(proxy2)}", "{makerdao_pot.address}", "{int_to_32byteshexstr(account2_join1_deposit // 10 ** 27)}"], "data": "0x1", "blockNumber": "{hex(params.account2_join1_blocknumber)}", "timeStamp": "{hex(blocknumber_to_timestamp(params.account2_join1_blocknumber))}", "gasPrice": "0x1", "gasUsed": "0x1", "logIndex": "0x6c", "transactionHash": "0xd81bddb97599cfab91b9ee52b5c505ffa730b71f1e484dc46d0f4ecb57893d2f", "transactionIndex": "0x79"}}"""  # noqa: E501

    # Not sure how to convince pylint that this ChecksumEvmAddress IS a subscriptable object
    proxy1_contents = proxy1[2:].lower()
    proxy2_contents = proxy2[2:].lower()

    dsr_params = params

    def mock_requests_get(url: str, params: dict[str, str], *args: Any, **kwargs) -> _patch | MockResponse:  # noqa: E501
        if url == ETHERSCAN_API_URL and {'module': 'proxy', 'action': 'eth_blockNumber'}.items() <= params.items():  # noqa: E501
            response = f'{{"status":"1","message":"OK","result":"{TEST_LATEST_BLOCKNUMBER_HEX}"}}'
        elif url == ETHERSCAN_API_URL and {'module': 'proxy', 'action': 'eth_call'}.items() <= params.items():  # noqa: E501
            to_address = params.get('to')
            input_data = params.get('data', '')
            if to_address == ds_proxy_registry.address:
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
            elif to_address == eth_multicall.address:
                web3 = Web3()
                contract = web3.eth.contract(address=eth_multicall.address, abi=eth_multicall.abi)
                fn_abi: Any = contract.functions.abi[0]
                assert fn_abi['name'] == 'aggregate', 'Abi position of multicall aggregate changed'
                output_types = get_abi_output_types(fn_abi)
                args = (1, proxies)
                result = '0x' + web3.codec.encode(output_types, args).hex()
                response = f'{{"status":"1","message":"OK","result":"{result}"}}'
            elif to_address == makerdao_pot.address:
                if input_data.startswith('0x0bebac86'):  # pie
                    if proxy1_contents in input_data:
                        result = int_to_32byteshexstr(dsr_params.account1_current_normalized_balance)  # noqa: E501
                    elif proxy2_contents in input_data:
                        result = int_to_32byteshexstr(dsr_params.account2_current_normalized_balance)  # noqa: E501
                    else:
                        raise AssertionError('Pie call for unexpected account during tests')
                elif input_data.startswith('0xc92aecc4'):  # chi
                    result = int_to_32byteshexstr(dsr_params.current_chi)
                elif input_data.startswith('0x487bf082'):  # dsr
                    result = int_to_32byteshexstr(dsr_params.current_dsr)
                else:
                    raise AssertionError(
                        'Call to unexpected method of MakerDao pot during tests',
                    )

                response = f'{{"status":"1","message":"OK","result":"{result}"}}'

            else:
                raise AssertionError(
                    f'Etherscan call to unknown contract {to_address} during tests',
                )
        elif url == ETHERSCAN_API_URL and {'module': 'logs', 'action': 'getLogs'}.items() <= params.items():  # noqa: E501
            contract_address = params.get('address')
            topic0 = params.get('topic0', '')
            topic1 = params.get('topic1', '')
            topic2 = params.get('topic1', '')
            from_block = int(params.get('fromBlock', ''))
            to_block = int(params.get('toBlock', ''))

            if contract_address == makerdao_pot.address:
                if topic0.startswith('0x049878f3'):  # join

                    events = []
                    if proxy1_contents in topic1:
                        if from_block <= dsr_params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_event)
                        if from_block <= dsr_params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_event)
                    elif proxy2_contents in topic1:
                        if from_block <= dsr_params.account2_join1_blocknumber <= to_block:
                            events.append(account2_join1_event)
                    else:
                        raise AssertionError(
                            f'Etherscan log query to makerdao POT contract for '
                            f'join for unknown account {topic1}',
                        )
                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'

                elif topic0.startswith('0x7f8661a1'):  # exit
                    events = []
                    if proxy1_contents in topic1 and from_block <= dsr_params.account1_exit1_blocknumber <= to_block:  # noqa: E501
                        events.append(account1_exit1_event)

                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'
                else:
                    raise AssertionError('Etherscan unknown log query to makerdao POT contract')

            elif contract_address == makerdao_vat.address:
                if topic0.startswith('0xbb35783b'):  # move
                    events = []
                    if proxy1_contents in topic1:  # deposit from acc1
                        if from_block <= dsr_params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_move_event)
                        if from_block <= dsr_params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_move_event)
                    elif proxy2_contents in topic1 and from_block <= dsr_params.account2_join1_blocknumber <= to_block:  # deposit from acc2  # noqa: E501
                        events.append(account2_join1_move_event)
                    elif proxy1_contents in topic2 and from_block <= dsr_params.account1_exit1_blocknumber <= to_block:  # withdrawal from acc1  # noqa: E501

                        events.append(account1_exit1_move_event)

                    response = f'{{"status":"1","message":"OK","result":[{",".join(events)}]}}'
                else:
                    raise AssertionError('Etherscan unknown log query to makerdao VAT contract')
            elif contract_address == makerdao_dai_join.address:
                events = []
                if topic0.startswith('0x3b4da69f'):  # join
                    if proxy1_contents in topic1:  # deposit from acc1
                        if from_block <= dsr_params.account1_join1_blocknumber <= to_block:
                            events.append(account1_join1_move_event)
                        if from_block <= dsr_params.account1_join2_blocknumber <= to_block:
                            events.append(account1_join2_move_event)
                    elif proxy2_contents in topic1 and from_block <= dsr_params.account2_join1_blocknumber <= to_block:  # deposit from acc2  # noqa: E501
                        events.append(account2_join1_move_event)
                elif topic0.startswith('0xef693bed'):  # exit
                    if from_block <= dsr_params.account1_exit1_blocknumber <= to_block:
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
        contracts: EvmContracts,
        accounts: list[ChecksumEvmAddress],
        original_requests_get: Callable,
) -> DSRTestSetup:
    account1 = accounts[0]
    account2 = accounts[1]

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
        contracts=contracts,
        account1=account1,
        account2=account2,
        original_requests_get=original_requests_get,
        params=params,
    )

    dsr_balance_response = {
        'current_dsr': '8.02277406522058107533312007531401770762840532683385494120377820398034738503100',  # noqa: E501
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


def assert_dsr_current_result_is_correct(result: dict[str, Any], setup: DSRTestSetup) -> None:
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
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_tests_for_dsr(
        etherscan=rotki.chains_aggregator.ethereum.node_inquirer.etherscan,
        contracts=rotki.chains_aggregator.ethereum.node_inquirer.contracts,
        accounts=ethereum_accounts,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'makerdaodsrbalanceresource',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

    assert_dsr_current_result_is_correct(outcome, setup)


@pytest.mark.parametrize('number_of_eth_accounts', [3])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_historical_dsr_non_premium(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_tests_for_dsr(
        etherscan=rotki.chains_aggregator.ethereum.node_inquirer.etherscan,
        contracts=rotki.chains_aggregator.ethereum.node_inquirer.contracts,
        accounts=ethereum_accounts,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'makerdaodsrhistoryresource',
        ))

    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.FORBIDDEN,
    )


def assert_dsr_history_result_is_correct(result: dict[str, Any], setup: DSRTestSetup) -> None:
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
                        elif mov_key in {'gain_so_far', 'value'}:
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
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts:  list[ChecksumEvmAddress],
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """Test DSR history is correctly queried

    This (and the async version) is a very hard to maintain test due to mocking
    everything.

    TODO: Perhaps change it to querying etherscan/chain until a given block for a
    given DSR account and check that until then all data match.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_tests_for_dsr(
        etherscan=rotki.chains_aggregator.ethereum.node_inquirer.etherscan,
        contracts=rotki.chains_aggregator.ethereum.node_inquirer.contracts,
        accounts=ethereum_accounts,
        original_requests_get=requests.get,
    )
    with setup.etherscan_patch:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'makerdaodsrhistoryresource',
        ), json={'async_query': async_query})
        outcome = assert_proper_response_with_result(
            response=response,
            rotkehlchen_api_server=rotkehlchen_api_server,
            async_query=async_query,
        )

    assert_dsr_history_result_is_correct(outcome, setup)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('mocked_current_prices', [{A_DAI: ONE}])
@pytest.mark.parametrize('mocked_proxies', [
    {TEST_ADDRESS_1: '0xAe9996b76bdAa003ace6D66328A6942565f5768d'},
])
def test_query_historical_dsr_with_a_zero_withdrawal(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """Test DSR for an account that was opened while DSR is 0 and made a 0 DAI withdrawal

    Essentially reproduce DSR problem reported here: https://github.com/rotki/rotki/issues/1032

    The account in question operates in a zero DSR environment but the reported
    problem seems to be just because he tried a zero DAI withdrawal
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    original_get_logs = rotki.chains_aggregator.ethereum.node_inquirer.get_logs

    # Query only until a block we know DSR is 0 and we know the number
    # of DSR events
    def mock_get_logs(
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            event_name: str,
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: Literal['latest'] = 'latest',  # pylint: disable=unused-argument
            call_order: None = None,
    ) -> list[dict[str, Any]]:
        return original_get_logs(
            contract_address,
            abi,
            event_name,
            argument_filters,
            from_block,
            to_block=10149816,  # A block at which DSR is still zero
            call_order=call_order,
        )

    patched_get_logs = patch.object(
        rotki.chains_aggregator.ethereum.node_inquirer,
        'get_logs',
        side_effect=mock_get_logs,
    )

    with patched_get_logs:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'makerdaodsrhistoryresource',
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
    assert_serialized_lists_equal(movements, expected_movements, max_diff='1e-26')
    errors = rotki.msg_aggregator.consume_errors()
    assert len(errors) == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf753beFE986e8Be8EBE7598C9d2b6297D9DD6662']])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_dsr_for_account_with_proxy_but_no_dsr(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Assure that an account with a DSR proxy but no DSR balance isn't returned in the balances"""
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'makerdaodsrbalanceresource',
    ))
    assert_proper_response(response)
    json_data = response.json()
    assert json_data['message'] == ''
    assert len(json_data['result']['balances']) == 0
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'makerdaodsrhistoryresource',
    ))
    json_data = response.json()
    assert json_data['message'] == ''
    assert len(json_data['result']) == 0
