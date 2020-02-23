from typing import Dict, NamedTuple
from unittest.mock import _patch, patch

import pytest
import requests

from rotkehlchen.constants.ethereum import MAKERDAO_POT_ADDRESS, MAKERDAO_PROXY_REGISTRY_ADDRESS
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.makerdao import _dsrdai_to_dai
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ChecksumEthAddress

TEST_LATEST_BLOCKNUMBER = 9540749
TEST_LATEST_BLOCKNUMBER_HEX = hex(TEST_LATEST_BLOCKNUMBER)


def int_to_32byteshexstr(value: int) -> str:
    return '0x' + value.to_bytes(32, byteorder='big').hex()


class DSRTestSetup(NamedTuple):
    etherscan_patch: _patch
    dsr_balance_response: Dict[ChecksumEthAddress, str]


def mock_etherscan_for_dsr(
        etherscan: Etherscan,
        account1: ChecksumEthAddress,
        account2: ChecksumEthAddress,
        original_requests_get,
        acc1_normalized_balance: int,
        acc2_normalized_balance: int,
        current_chi: int,
) -> _patch:

    proxy1 = make_ethereum_address()
    proxy2 = make_ethereum_address()

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
                    proxy_account = '0x' + '0' * 24 + proxy1[2:].lower()
                elif account2[2:].lower() in input_data:
                    proxy_account = '0x' + '0' * 24 + proxy2[2:].lower()
                else:
                    proxy_account = '0x' + '0' * 64
                response = f'{{"status":"1","message":"OK","result":"{proxy_account}"}}'
            elif to_address == MAKERDAO_POT_ADDRESS:
                if input_data.startswith('0x0bebac86'):  # pie
                    if proxy1[2:].lower() in input_data:
                        result = int_to_32byteshexstr(acc1_normalized_balance)
                    elif proxy2[2:].lower() in input_data:
                        result = int_to_32byteshexstr(acc2_normalized_balance)
                    else:
                        # result = int_to_32byteshexstr(0)
                        raise AssertionError('Pie call for unexpected account during tests')
                elif input_data.startswith('0xc92aecc4'):  # chi
                    result = int_to_32byteshexstr(current_chi)
                else:
                    raise AssertionError(
                        'Call to unexpected method of MakerDAO pot during tests',
                    )

                response = f'{{"status":"1","message":"OK","result":"{result}"}}'

            else:
                raise AssertionError(
                    f'Etherscan call to unknown contract {to_address} during tests',
                )
            pass
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
    acc1_normalized_balance = 123232334324234324
    acc2_normalized_balance = 5323213213123534234
    current_chi = 1123323222211111111111001249911111
    etherscan_patch = mock_etherscan_for_dsr(
        etherscan=etherscan,
        account1=account1,
        account2=account2,
        original_requests_get=original_requests_get,
        acc1_normalized_balance=acc1_normalized_balance,
        acc2_normalized_balance=acc2_normalized_balance,
        current_chi=current_chi,
    )

    dsr_balance_response = {
        account1: _dsrdai_to_dai(acc1_normalized_balance * current_chi),
        account2: _dsrdai_to_dai(acc2_normalized_balance * current_chi),
    }
    return DSRTestSetup(etherscan_patch=etherscan_patch, dsr_balance_response=dsr_balance_response)


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
