import json
import re
from collections import namedtuple
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

import requests
from hexbytes import HexBytes

from rotkehlchen.tests.utils.avalanche import AVALANCHE_ACC1_AVAX_ADDR, AVALANCHE_ACC2_AVAX_ADDR
from rotkehlchen.types import SupportedBlockchain

original_requests_get = requests.get
MOCK_WEB3_LAST_BLOCK_INT = 16210873
MOCK_WEB3_LAST_BLOCK_HEX = '0xf75bb9'

MOCK_ROOT = Path(__file__).resolve().parent.parent / 'data' / 'mocks'


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


def patch_web3_request(given_web3, test_specific_mock_data):
    """Patches all requests going to web3 through the given provider

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

    return patch.object(
        given_web3.provider,
        'make_request',
        wraps=mock_web3_make_request,
    )


ETHERSCAN_ACTION_RE = re.compile('.*action=(.*?)&(.*)')
ETHERSCAN_ETH_CALL_RE = re.compile('&to=(.*)&data=(.*)&.*')
ETHERSCAN_BLOCKNOBYTIME_RE = re.compile('&timestamp=(.*)&closest=(.*)&.*')


def _mock_etherscan_eth_call(counter, url, eth_call_data):
    match = ETHERSCAN_ETH_CALL_RE.search(url)
    if match is None:
        raise AssertionError(f'Could not parse etherscan query: {url} for eth call')

    contract_to = match.group(1)
    data = match.group(2)
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
    return f'{{"id": {counter}, "jsonrpc": "2.0", "result": "{result}"}}'


def _mock_etherscan_getblocknobytime(url, data):
    match = ETHERSCAN_BLOCKNOBYTIME_RE.search(url)
    if match is None:
        raise AssertionError(f'Could not parse etherscan query: {url} for blocknobytime')

    timestamp = match.group(1)
    closest = match.group(2)
    if data is None:
        raise AssertionError('No blocknobytime mock data given in test')

    block_result = data.get(timestamp)
    if block_result is None:
        raise AssertionError(f'{timestamp=} not found in blocknobytime mock data')

    assert closest == 'before'
    return f'{{"status":"1","message":"OK","result":"{block_result}"}}'


def patch_etherscan_request(etherscan, mock_data: dict[str, Any]):
    """Patches all requests going to the passed etherscan object with the given data"""
    counter = 0

    def mock_etherscan_query(url, **kwargs):  # pylint: disable=unused-argument
        nonlocal counter
        match = ETHERSCAN_ACTION_RE.search(url)
        if match is None:
            raise AssertionError(f'Could not parse etherscan query: {url}')

        action = match.group(1)
        if action == 'eth_call':
            contents = _mock_etherscan_eth_call(counter, url, mock_data.get(action))
        elif action == 'getblocknobytime':
            contents = _mock_etherscan_getblocknobytime(url, mock_data.get(action))
        else:
            raise AssertionError(f'Unexpected action {action} at etherscan query parsing: {url}')

        counter += 1
        return MockResponse(200, contents)

    return patch.object(
        etherscan.session,
        'get',
        wraps=mock_etherscan_query,
    )


BEACONCHAIN_ETH1_CALL_RE = re.compile('https://beaconcha.in/api/v1/validator/eth1/(.*)')
BEACONCHAIN_OTHER_CALL_RE = re.compile('https://beaconcha.in/api/v1/validator/(.*)/(.*)')


def patch_eth2_requests(eth2, mock_data):
    """Patches all requests going to the passed Eth2 object"""

    def mock_beaconchain_query(url, **kwargs):  # pylint: disable=unused-argument
        response_data = {'data': [], 'status': 'OK'}
        eth1_match = BEACONCHAIN_ETH1_CALL_RE.search(url)
        if eth1_match is not None:
            eth1_address = eth1_match.group(1)
            eth1_data = mock_data.get('eth1')
            if eth1_data is None:
                raise AssertionError(f'No eth1 mock data for beaconchain call: {url}')
            validator_data = eth1_data.get(eth1_address)
            if validator_data is None:
                raise AssertionError(f'No eth1 address in mock data for address: {eth1_address}')

            response_validators = []
            for entry in validator_data:
                response_validators.append({
                    'publickey': entry[0],
                    'valid_signature': entry[1],
                    'validatorindex': entry[2],
                })
            response_data['data'] = response_validators

        elif (other_match := BEACONCHAIN_OTHER_CALL_RE.search(url)) is not None:
            endpoint = other_match.group(2)
            encoded_args = other_match.group(1)
            if endpoint == 'deposits':
                deposit_data = mock_data.get('deposits')
                if deposit_data is None:
                    raise AssertionError(f'No mock deposit data for beacon chain call: {url}')
                # for now let's just compare length of arguments to choose mock response
                arg_len = len(encoded_args.split(','))
                file_result = deposit_data.get(arg_len)
                if file_result is None:
                    raise AssertionError(f'Deposit data for {arg_len} addresses not found in mock data')  # noqa: E501
                fullpath = MOCK_ROOT / 'test_eth2' / 'deposits' / file_result
                with open(fullpath) as f:
                    response_data = json.load(f)
            else:
                raise AssertionError(f'Unknown endpoint for beacon chain call: {url}')

        return MockResponse(200, json.dumps(response_data, separators=(',', ':')))
    return patch.object(
        eth2.beaconchain.session,
        'get',
        wraps=mock_beaconchain_query,
    )


COVALENT_RE = re.compile(r'https://api.covalenthq.com/v1/(\d+)/(.*)/(.*)/(.*)/.*')


def patch_avalanche_request(avalanche_manager, mock_data):

    def mock_covalent_query(url, **kwargs):  # pylint: disable=unused-argument
        match = COVALENT_RE.search(url)
        if match is None:  # only for eth_call for now
            raise AssertionError(f'Could not parse covalent query: {url}')

        action = match.group(2)
        address = match.group(3)
        module = match.group(4)

        if module == 'transactions_v2':
            assert address == '0x350f13c2C46AcaC8e44711F4bD87321304572A7D'
            if action != 'address':
                raise AssertionError(f'Unknown covalent query {url}')

            covalent_tx_path = mock_data.get('covalent_transactions')
            if covalent_tx_path is None:
                raise AssertionError('Test mock data should contain covalent transactions')

            fullpath = MOCK_ROOT / covalent_tx_path
            with open(fullpath) as f:
                response_data = json.load(f)
        elif module == 'balances_v2':
            if action != 'address':
                raise AssertionError(f'Unknown covalent query {url}')

            if address in (AVALANCHE_ACC1_AVAX_ADDR, AVALANCHE_ACC2_AVAX_ADDR):
                # Since the test doesnt really test for balance values, use same response for all
                covalent_balances_path = mock_data.get('covalent_balances')
                if covalent_balances_path is None:
                    raise AssertionError('Test mock data should contain covalent balances')
                fullpath = MOCK_ROOT / covalent_balances_path
                with open(fullpath) as f:
                    response_data = json.load(f)
            else:
                raise AssertionError(f'Covalent balance query for unknown address during tests: {url}')  # noqa: E501
        else:
            raise AssertionError(f'Covalent query for unknown module: {url}')

        return MockResponse(200, json.dumps(response_data, separators=(',', ':')))

    return patch.object(
        avalanche_manager.covalent.session,
        'get',
        side_effect=mock_covalent_query,
    )


def mock_proxies(mocked_proxies):
    return patch(
        'rotkehlchen.chain.evm.proxies_inquirer.EvmProxiesInquirer.get_accounts_having_proxy',
        return_value=mocked_proxies,
    )


def mock_evm_chains_with_transactions():
    return patch(
        'rotkehlchen.tasks.manager.EVM_CHAINS_WITH_TRANSACTIONS',
        new=(SupportedBlockchain.ETHEREUM,),
    )
