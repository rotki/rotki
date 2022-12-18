import json
import re
from collections import namedtuple
from typing import Any, Optional
from unittest.mock import patch

from hexbytes import HexBytes

MOCK_WEB3_LAST_BLOCK_INT = 16210873
MOCK_WEB3_LAST_BLOCK_HEX = '0xf75bb9'


class MockResponse():
    def __init__(
            self,
            status_code: int,
            text: str,
            headers: Optional[dict['str', Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.content = text.encode()
        self.url = 'http://someurl.com'
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return json.loads(self.text)


class MockEth():

    syncing = False

    def __init__(self, block_number: int) -> None:
        self.block_number = block_number
        self.chainId = 1

    def get_block(
            self,
            _number: int,
    ) -> dict[str, HexBytes]:
        """Always return genesis block since this is what we care about in the tests"""
        genesis = (
            b'\xd4\xe5g@\xf8v\xae\xf8\xc0\x10\xb8j@\xd5\xf5gE\xa1\x18\xd0\x90j4'
            b'\xe6\x9a\xec\x8c\r\xb1\xcb\x8f\xa3'
        )
        return {'hash': HexBytes(genesis)}


class MockMiddlewareOnion():

    def inject(self, middleware, layer) -> None:
        pass


class MockWeb3():

    def __init__(self, providers=None, middlewares=None, ens=None):  # pylint: disable=unused-argument  # noqa: E501
        self.eth = MockEth(0)
        self.middleware_onion = MockMiddlewareOnion()

    def isConnected(self) -> bool:  # mocking existing function # noqa: N802
        return True

    @property
    def net(self):
        return namedtuple('Version', ['version'])(version=1)


def patch_web3_request(test_specific_mock_data):
    """Patches all requests going to web3 through the rpc provider

    Has some pre-determined mock responses but also accepts test_specific_mock_data
    to determine certain responses per-test
    """
    counter = 0
    method_dict = {
        'web3_clientVersion': 'Geth/v1.10.23-omnibus-b38477ec/linux-amd64/go1.18.5',
        'net_version': '1',
        'eth_blockNumber': MOCK_WEB3_LAST_BLOCK_HEX,
        'eth_chainId': '0x1',
    }
    method_dict.update(test_specific_mock_data)

    def mock_web3_make_request(method: str, params: tuple):
        """A mock for all web3 rpc requests"""
        nonlocal counter
        final_result = None
        result = method_dict.get(method)
        if result is None:
            raise AssertionError(f'No web3 mock for {method} and {params}')

        if isinstance(result, str):
            final_result = result
        elif isinstance(result, dict):
            if method != 'eth_call':
                raise AssertionError(f'Got dict result for non eth_call mock: {method} and {params}')  # noqa: E501
            contract_to = params[0]['to']
            if contract_to not in result:
                raise AssertionError(f'eth_call to {contract_to} has no mock')

            data = params[0]['data']
            if data not in result[contract_to]:
                raise AssertionError(f'eth_call to {contract_to} for {data} has no mock')

            block = params[1]
            if block not in result[contract_to][data]:
                raise AssertionError(f'eth_call to {contract_to} for {data} and block {block} has no mock')  # noqa: E501

            final_result = result[contract_to][data][block]
        else:
            raise AssertionError(f'Unrecognized web3 mock result type: {type(result)}')

        json_result = {'id': counter, 'jsonrpc': '2.0', 'result': final_result}
        counter += 1
        return json_result

    return patch(
        'web3.providers.rpc.HTTPProvider.make_request',
        wraps=mock_web3_make_request,
    )


ETHERSCAN_ETH_CALL_RE = re.compile('.*action=(.*)&to=(.*)&data=(.*)&.*')


def patch_etherscan_request(etherscan, mock_data):
    """Patches all requests going to the passed etherscan object with the given data"""
    counter = 0

    def mock_etherscan_query(url, **kwargs):  # pylint: disable=unused-argument
        nonlocal counter
        match = ETHERSCAN_ETH_CALL_RE.search(url)
        if match is None:  # only for eth_call for now
            raise AssertionError(f'Could not parse etherscan query: {url}')

        contract_to = match.group(2)
        data = match.group(3)

        eth_call_data = mock_data.get('eth_call')
        if eth_call_data is None:
            raise AssertionError(f'No eth_call mock data given in test for {contract_to=} and {data=}')  # noqa: E501

        contract_result = eth_call_data.get(contract_to)
        if contract_result is None:
            raise AssertionError(f'{contract_to=} not found in eth_call mock data')

        data_result = contract_result.get(data)
        if data_result is None:
            raise AssertionError(f'{data=} not found in eth_call mock data for contract {contract_to}')  # noqa: E501

        if 'latest' not in data_result:
            raise AssertionError(f'No latest mock result given in test for {contract_to=} and {data=}')  # noqa: E501

        result = data_result['latest']
        contents = f'{{"id": {counter}, "jsonrpc": "2.0", "result": "{result}"}}'
        return MockResponse(200, contents)

    return patch.object(
        etherscan.session,
        'get',
        wraps=mock_etherscan_query,
    )
