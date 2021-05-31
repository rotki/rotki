import json
import logging
from typing import Any, Dict, List, Optional, Union
from unittest.mock import patch

from web3 import Web3
from web3._utils.abi import get_abi_input_types, get_abi_output_types

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.ethereum import ETH_MULTICALL, ETH_SCAN, ZERION_ABI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, UnknownAsset
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.tests.utils.eth_tokens import CONTRACT_ADDRESS_TO_TOKEN
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc

logger = logging.getLogger(__name__)


def assert_btc_balances_result(
        result: Dict[str, Any],
        btc_accounts: List[str],
        btc_balances: List[str],
        also_eth: bool,
) -> None:
    """Asserts for correct BTC blockchain balances when mocked in tests"""
    per_account = result['per_account']
    if also_eth:
        assert len(per_account) == 2
    else:
        assert len(per_account) == 1
    per_account = per_account['BTC']
    assert len(per_account) == 1  # make sure we only have standalone accounts in these tests
    standalone = per_account['standalone']
    msg = 'standalone results num does not match number of btc accounts'
    assert len(standalone) == len(btc_accounts), msg
    msg = 'given balances and accounts should have same length'
    assert len(btc_accounts) == len(btc_balances), msg
    for idx, account in enumerate(btc_accounts):
        balance = satoshis_to_btc(FVal(btc_balances[idx]))
        assert FVal(standalone[account]['amount']) == balance
        if balance == ZERO:
            assert FVal(standalone[account]['usd_value']) == ZERO
        else:
            assert FVal(standalone[account]['usd_value']) > ZERO

    if 'assets' in result['totals']:
        totals = result['totals']['assets']
    else:
        totals = result['totals']
    if also_eth:
        assert len(totals) >= 2  # ETH and any other tokens that may exist
    else:
        assert len(totals) == 1

    expected_btc_total = sum(satoshis_to_btc(FVal(balance)) for balance in btc_balances)
    assert FVal(totals['BTC']['amount']) == expected_btc_total
    if expected_btc_total == ZERO:
        assert FVal(totals['BTC']['usd_value']) == ZERO
    else:
        assert FVal(totals['BTC']['usd_value']) > ZERO


def assert_eth_balances_result(
        rotki: Rotkehlchen,
        result: Dict[str, Any],
        eth_accounts: List[str],
        eth_balances: List[str],
        token_balances: Dict[EthereumToken, List[str]],
        also_btc: bool,
        expected_liabilities: Dict[EthereumToken, List[str]] = None,
        totals_only: bool = False,
) -> None:
    """Asserts for correct ETH blockchain balances when mocked in tests

    If totals_only is given then this is a query for all balances so only the totals are shown
    """
    if not totals_only:
        per_account = result['per_account']
        if also_btc:
            assert len(per_account) == 2
        else:
            assert len(per_account) == 1
        per_account = per_account['ETH']
        assert len(per_account) == len(eth_accounts)
        for idx, account in enumerate(eth_accounts):
            expected_amount = from_wei(FVal(eth_balances[idx]))
            amount = FVal(per_account[account]['assets']['ETH']['amount'])
            usd_value = FVal(per_account[account]['assets']['ETH']['usd_value'])
            assert amount == expected_amount
            if amount == ZERO:
                assert usd_value == ZERO
            else:
                assert usd_value > ZERO
            for token, balances in token_balances.items():
                expected_token_amount = FVal(balances[idx])
                if expected_token_amount == ZERO:
                    msg = f'{account} should have no entry for {token}'
                    assert token.identifier not in per_account[account], msg
                else:
                    token_amount = FVal(per_account[account]['assets'][token.identifier]['amount'])
                    usd_value = FVal(
                        per_account[account]['assets'][token.identifier]['usd_value'],
                    )
                    assert token_amount == from_wei(expected_token_amount)
                    assert usd_value > ZERO

    if totals_only:
        totals = result
    else:
        totals = result['totals']['assets']

    if expected_liabilities is not None:
        per_account = result['per_account']['ETH']
        for token, balances in expected_liabilities.items():
            total_amount = ZERO
            for idx, account in enumerate(eth_accounts):
                amount = FVal(per_account[account]['liabilities'][token.identifier]['amount'])
                assert amount == FVal(balances[idx])
                total_amount += amount

            assert FVal(result['totals']['liabilities'][token.identifier]['amount']) == total_amount  # noqa: E501

    # Check our owned eth tokens here since the test may have changed their number
    owned_assets = set(rotki.chain_manager.totals.assets.keys())
    if not also_btc:
        owned_assets.discard(A_BTC)
    assert len(totals) == len(owned_assets)

    expected_total_eth = sum(from_wei(FVal(balance)) for balance in eth_balances)
    assert FVal(totals['ETH']['amount']) == expected_total_eth
    if expected_total_eth == ZERO:
        assert FVal(totals['ETH']['usd_value']) == ZERO
    else:
        assert FVal(totals['ETH']['usd_value']) > ZERO

    for token, balances in token_balances.items():
        symbol = token.identifier

        expected_total_token = sum(from_wei(FVal(balance)) for balance in balances)
        assert FVal(totals[symbol]['amount']) == expected_total_token
        if expected_total_token == ZERO:
            msg = f"{FVal(totals[symbol]['usd_value'])} is not ZERO"
            assert FVal(totals[symbol]['usd_value']) == ZERO, msg
        else:
            assert FVal(totals[symbol]['usd_value']) > ZERO


def _get_token(value: Any) -> Optional[EthereumToken]:
    """Interprets the given value as token if possible"""
    if isinstance(value, str):
        try:
            token = EthereumToken(value)
        except (UnknownAsset, DeserializationError):
            # not a token
            return None
        return token
    if isinstance(value, EthereumToken):
        return value
    # else
    return None


def mock_beaconchain(
        beaconchain: BeaconChain,
        original_queries: Optional[List[str]],
        original_requests_get,
):

    def mock_requests_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        if original_queries is not None and 'beaconchain' in original_queries:
            return original_requests_get(url, *args, **kwargs)

        if 'validator' in url:  # all validators that belong to an eth1 address
            response = '{"status":"OK","data":[]}'
        else:
            raise AssertionError(f'Unrecognized argument url for beaconchain mock in tests: {url}')

        return MockResponse(200, response)

    return patch.object(beaconchain.session, 'get', wraps=mock_requests_get)


def mock_etherscan_query(
        eth_map: Dict[ChecksumEthAddress, Dict[Union[str, EthereumToken], Any]],
        etherscan: Etherscan,
        original_queries: Optional[List[str]],
        extra_flags: Optional[List[str]],
        original_requests_get,
):
    original_queries = [] if original_queries is None else original_queries
    extra_flags = [] if extra_flags is None else extra_flags

    def mock_requests_get(url, *args, **kwargs):
        if 'etherscan.io/api?module=account&action=balance&address' in url:
            addr = url[67:109]
            value = eth_map[addr].get('ETH', '0')
            response = f'{{"status":"1","message":"OK","result":{value}}}'

        elif 'etherscan.io/api?module=account&action=balancemulti' in url:
            queried_accounts = []
            length = 72
            # process url and get the accounts
            while True:
                if len(url) < length:
                    break
                potential_address = url[length:length + 42]
                if 'apikey=' in potential_address:
                    break
                queried_accounts.append(potential_address)
                length += 43

            accounts = []
            for addr in queried_accounts:
                value = eth_map[addr].get('ETH', '0')
                accounts.append({'account': addr, 'balance': eth_map[addr]['ETH']})
            response = f'{{"status":"1","message":"OK","result":{json.dumps(accounts)}}}'

        elif 'api.etherscan.io/api?module=account&action=tokenbalance' in url:
            token_address = url[80:122]
            msg = 'token address missing from test mapping'
            assert token_address in CONTRACT_ADDRESS_TO_TOKEN, msg
            response = '{"status":"1","message":"OK","result":"0"}'
            token = CONTRACT_ADDRESS_TO_TOKEN[token_address]
            account = url[131:173]
            value = eth_map[account].get(token.identifier, 0)
            response = f'{{"status":"1","message":"OK","result":"{value}"}}'
        elif 'api.etherscan.io/api?module=account&action=txlistinternal&' in url:
            if 'transactions' in original_queries:
                return original_requests_get(url, *args, **kwargs)
            # By default when mocking, don't query for transactions
            response = '{"status":"1","message":"OK","result":[]}'
        elif 'api.etherscan.io/api?module=account&action=txlist&' in url:
            if 'transactions' in original_queries:
                return original_requests_get(url, *args, **kwargs)
            # By default when mocking, don't query for transactions
            response = '{"status":"1","message":"OK","result":[]}'
        elif 'api.etherscan.io/api?module=logs&action=getLogs&' in url:
            if 'logs' in original_queries:
                return original_requests_get(url, *args, **kwargs)
            # By default when mocking, don't query logs
            response = '{"status":"1","message":"OK","result":[]}'
        elif 'api.etherscan.io/api?module=block&action=getblocknobytime&' in url:
            if 'blocknobytime' in original_queries:
                return original_requests_get(url, *args, **kwargs)
            # By default when mocking don't query blocknobytime
            response = '{"status":"1","message":"OK","result":"1"}'
        elif f'api.etherscan.io/api?module=proxy&action=eth_call&to={ZERION_ADAPTER_ADDRESS}' in url:  # noqa: E501
            if 'zerion' in original_queries:
                return original_requests_get(url, *args, **kwargs)

            web3 = Web3()
            contract = web3.eth.contract(address=ZERION_ADAPTER_ADDRESS, abi=ZERION_ABI)
            if 'data=0xc84aae17' in url:  # getBalances
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = contract._find_matching_fn_abi(
                    fn_identifier='getBalances',
                    args=['address'],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                # TODO: This here always returns empty response. If/when we want to
                # mock it for etherscan, this is where we do it
                args = []
                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif 'data=0x85c6a7930' in url:  # getProtocolBalances
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = contract._find_matching_fn_abi(
                    fn_identifier='getProtocolBalances',
                    args=['address', ['some', 'protocol', 'names']],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                # TODO: This here always returns empty response. If/when we want to
                # mock it for etherscan, this is where we do it
                args = []
                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif 'data=0x3b692f52' in url:  # getProtocolNames
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = contract._find_matching_fn_abi(
                    fn_identifier='getProtocolNames',
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                # TODO: This here always returns empty response. If/when we want to
                # mock it for etherscan, this is where we do it
                args = []
                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            else:
                raise AssertionError(f'Unexpected etherscan call during tests: {url}')
        elif 'api.etherscan.io/api?module=proxy&action=eth_call&to=0xB6456b57f03352bE48Bf101B46c1752a0813491a' in url:  # noqa: E501  # ADEX Staking contract
            if 'adex_staking' in original_queries:
                return original_requests_get(url, *args, **kwargs)

            if 'data=0x447b15f4' in url:  # a mocked share value
                response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000fc4a48782d85b51"}'  # noqa: E501
            else:
                raise AssertionError(f'Unknown call to Adex Staking pool during tests: {url}')
        elif f'api.etherscan.io/api?module=proxy&action=eth_call&to={ETH_MULTICALL.address}' in url:  # noqa: E501
            web3 = Web3()
            contract = web3.eth.contract(address=ETH_MULTICALL.address, abi=ETH_MULTICALL.abi)
            if 'b6456b57f03352be48bf101b46c1752a0813491a' in url:
                multicall_purpose = 'adex_staking'
            elif '5f3b5dfeb7b28cdbd7faba78963ee202a494e2a2' in url:
                multicall_purpose = 'vecrv'
            else:
                raise AssertionError('Unknown multicall in mocked tests')
            if 'data=0x252dba42' in url:  # aggregate
                if multicall_purpose == 'adex_staking':
                    if 'adex_staking' in original_queries:
                        return original_requests_get(url, *args, **kwargs)

                    if 'mocked_adex_staking_balance' in extra_flags:
                        # mock adex staking balance for a single account
                        response = '{"jsonrpc": "2.0", "id": 1, "result": "0x0000000000000000000000000000000000000000000000000000000000bb45aa000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000152982285d2e4d5aeaa9"}'  # noqa: E501
                        return MockResponse(200, response)

                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = contract.functions.abi[1]
                assert fn_abi['name'] == 'aggregate', 'Abi position of multicall aggregate changed'
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                # For now the only mocked multicall is 32 bytes for multicall balance
                # of both veCRV and adex staking pool.
                # When there is more we have to figure out a way to differentiate
                # between them in mocking. Just return empty response here
                # all pylint ignores below due to https://github.com/PyCQA/pylint/issues/4114
                args = [1, [b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' for x in decoded_input[0]]]  # pylint: disable=unsubscriptable-object  # noqa: E501
                result = '0x' + web3.codec.encode_abi(output_types, args).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            else:
                raise AssertionError('Unexpected etherscan multicall during tests: {url}')

        elif f'api.etherscan.io/api?module=proxy&action=eth_call&to={ETH_SCAN.address}' in url:
            if 'ethscan' in original_queries:
                return original_requests_get(url, *args, **kwargs)

            web3 = Web3()
            contract = web3.eth.contract(address=ETH_SCAN.address, abi=ETH_SCAN.abi)
            if 'data=0xdbdbb51b' in url:  # Eth balance query
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = contract._find_matching_fn_abi(
                    fn_identifier='etherBalances',
                    args=[list(eth_map.keys())],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                args = []
                for account_address in decoded_input[0]:  # pylint: disable=unsubscriptable-object  # noqa: E501
                    account_address = deserialize_ethereum_address(account_address)
                    args.append(int(eth_map[account_address]['ETH']))
                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif 'data=0x06187b4f' in url:  # Multi token multiaddress balance query
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]
                # not really the given args, but we just want the fn abi
                args = [list(eth_map.keys()), list(eth_map.keys())]
                fn_abi = contract._find_matching_fn_abi(
                    fn_identifier='tokensBalances',
                    args=args,
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                args = []
                for account_address in decoded_input[0]:  # pylint: disable=unsubscriptable-object  # noqa: E501
                    account_address = deserialize_ethereum_address(account_address)
                    x = []
                    for token_address in decoded_input[1]:  # pylint: disable=unsubscriptable-object  # noqa: E501
                        token_address = deserialize_ethereum_address(token_address)
                        value_to_add = 0
                        for given_asset, value in eth_map[account_address].items():
                            given_asset = _get_token(given_asset)
                            if given_asset is None:
                                # not a token
                                continue
                            if token_address != given_asset.ethereum_address:
                                continue
                            value_to_add = int(value)
                            break
                        x.append(value_to_add)
                    args.append(x)

                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'

            elif 'data=0xe5da1b68' in url:  # Multi token balance query
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]
                # not really the given args, but we just want the fn abi
                args = ['str', list(eth_map.keys())]
                fn_abi = contract._find_matching_fn_abi(
                    fn_identifier='tokensBalance',
                    args=args,
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                args = []
                account_address = deserialize_ethereum_address(decoded_input[0])  # pylint: disable=unsubscriptable-object  # noqa: E501
                x = []
                for token_address in decoded_input[1]:  # pylint: disable=unsubscriptable-object  # noqa: E501
                    token_address = deserialize_ethereum_address(token_address)
                    value_to_add = 0
                    for given_asset, value in eth_map[account_address].items():
                        given_asset = _get_token(given_asset)
                        if given_asset is None:
                            # not a token
                            continue

                        if token_address != given_asset.ethereum_address:
                            continue
                        value_to_add = int(value)
                        break
                    args.append(value_to_add)

                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            else:
                raise AssertionError(f'Unexpected etherscan call during tests: {url}')

        else:
            return original_requests_get(url, *args, **kwargs)

        return MockResponse(200, response)

    return patch.object(etherscan.session, 'get', wraps=mock_requests_get)


def mock_bitcoin_balances_query(
        btc_map: Dict[BTCAddress, str],
        original_requests_get,
):

    def mock_requests_get(url, *args, **kwargs):
        if 'blockchain.info' in url:
            addresses = url.split('multiaddr?active=')[1].split('|')
            response = '{"addresses":['
            for idx, address in enumerate(addresses):
                balance = btc_map.get(address, '0')
                response += f'{{"address":"{address}", "final_balance":{balance}}}'
                if idx < len(addresses) - 1:
                    response += ','
            response += ']}'
        elif 'blockstream.info' in url:
            split_result = url.rsplit('/', 1)
            if len(split_result) != 2:
                raise AssertionError(f'Could not find bitcoin address at url {url}')
            address = split_result[1]
            balance = btc_map.get(address, '0')
            response = f"""{{"address":"{address}","chain_stats":{{"funded_txo_count":1,"funded_txo_sum":{balance},"spent_txo_count":0,"spent_txo_sum":0,"tx_count":1}},"mempool_stats":{{"funded_txo_count":0,"funded_txo_sum":0,"spent_txo_count":0,"spent_txo_sum":0,"tx_count":0}}}}"""  # noqa: E501
        else:
            return original_requests_get(url, *args, **kwargs)

        return MockResponse(200, response)

    return patch('rotkehlchen.utils.network.requests.get', wraps=mock_requests_get)


def compare_account_data(expected: List[Dict], got: List[Dict]) -> None:
    """Compare two lists of account data dictionaries for equality"""

    for got_entry in got:
        found = False
        got_address = got_entry['address']
        for expected_entry in expected:
            if got_address == expected_entry['address']:
                found = True

                got_label = got_entry.get('label', None)
                expected_label = expected_entry.get('label', None)
                msg = (
                    f'Comparing account data for {got_address} got label {got_label} '
                    f'but expected label {expected_label}'
                )
                assert got_label == expected_label, msg

                got_tags = got_entry.get('tags', None)
                got_tags_str = 'no tags' if not got_tags else ','.join(got_tags)
                expected_tags = expected_entry.get('tags', None)
                expected_tags_str = 'no tags' if not expected_tags else ','.join(expected_tags)
                got_set = set(got_tags) if got_tags else None
                expected_set = set(expected_tags) if expected_tags else None
                msg = (
                    f'Comparing account data for {got_address} got tags [{got_tags_str}] '
                    f'but expected tags [{expected_tags_str}]'
                )
                assert got_set == expected_set, msg

        msg = (
            f'Comparing account data could not find entry for address '
            f'{got_address} in expected data'
        )
        assert found, msg
