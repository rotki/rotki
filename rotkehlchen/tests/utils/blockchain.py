import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Optional, Union
from unittest.mock import patch

from web3 import Web3
from web3._utils.abi import get_abi_input_types, get_abi_output_types

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.evm.types import NodeName, Web3Node, string_to_evm_address
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.beaconchain import BeaconChain
from rotkehlchen.externalapis.etherscan import Etherscan, EtherscanHasChainActivity
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tests.utils.eth_tokens import CONTRACT_ADDRESS_TO_TOKEN
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import BTCAddress, ChecksumEvmAddress, SupportedBlockchain
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc

if TYPE_CHECKING:
    from contextlib import ExitStack

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.db.dbhandler import DBHandler


def assert_btc_balances_result(
        result: dict[str, Any],
        btc_accounts: list[str],
        btc_balances: list[str],
        also_eth: bool,
) -> None:
    """Asserts for correct BTC blockchain balances when mocked in tests"""
    per_account = result['per_account']
    if also_eth:
        assert len(per_account) == 2
    else:
        assert len(per_account) == 1
    per_account = per_account['btc']
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

    totals = result['totals'].get('assets', result['totals'])
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
        result: dict[str, Any],
        eth_accounts: list[str],
        eth_balances: list[str],
        token_balances: dict[EvmToken, list[str]],
        also_btc: bool,
        expected_liabilities: Optional[dict[EvmToken, list[str]]] = None,
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
        per_account = per_account[SupportedBlockchain.ETHEREUM.serialize()]
        assert len(per_account) == len(eth_accounts)
        for idx, account in enumerate(eth_accounts):
            expected_amount = from_wei(FVal(eth_balances[idx]))
            amount = FVal(per_account[account]['assets'][A_ETH.identifier]['amount'])
            usd_value = FVal(per_account[account]['assets'][A_ETH.identifier]['usd_value'])
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
        per_account = result['per_account'][SupportedBlockchain.ETHEREUM.serialize()]
        for token, balances in expected_liabilities.items():
            total_amount = ZERO
            for idx, account in enumerate(eth_accounts):
                amount = FVal(per_account[account]['liabilities'][token.identifier]['amount'])
                assert amount == FVal(balances[idx])
                total_amount += amount

            assert FVal(result['totals']['liabilities'][token.identifier]['amount']) == total_amount  # noqa: E501

    # Check our owned eth tokens here since the test may have changed their number
    owned_assets = set(rotki.chains_aggregator.totals.assets.keys())
    if not also_btc:
        owned_assets.discard(A_BTC)
    assert len(totals) == len(owned_assets)

    expected_total_eth = sum(from_wei(FVal(balance)) for balance in eth_balances)
    assert FVal(totals[A_ETH.identifier]['amount']) == expected_total_eth
    if expected_total_eth == ZERO:
        assert FVal(totals[A_ETH.identifier]['usd_value']) == ZERO
    else:
        assert FVal(totals[A_ETH.identifier]['usd_value']) > ZERO

    for token, balances in token_balances.items():
        symbol = token.identifier

        expected_total_token = sum(from_wei(FVal(balance)) for balance in balances)
        assert FVal(totals[symbol]['amount']) == expected_total_token
        if expected_total_token == ZERO:
            msg = f"{FVal(totals[symbol]['usd_value'])} is not ZERO"
            assert FVal(totals[symbol]['usd_value']) == ZERO, msg
        else:
            assert FVal(totals[symbol]['usd_value']) > ZERO


def _get_token(value: Any) -> Optional[EvmToken]:
    """Interprets the given value as token if possible"""
    if isinstance(value, str):
        try:
            identifier = strethaddress_to_identifier(value)
            token = EvmToken(identifier)
        except (UnknownAsset, DeserializationError):
            # not a token
            return None
        return token
    if isinstance(value, EvmToken):
        return value
    if isinstance(value, Asset):
        try:
            return value.resolve_to_evm_token()
        except (WrongAssetType, UnknownAsset):
            return None
    # else
    return None


def mock_beaconchain(
        beaconchain: BeaconChain,
        original_queries: Optional[list[str]],
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
        eth_map: dict[ChecksumEvmAddress, dict[Union[str, EvmToken], Any]],
        etherscan: Etherscan,
        ethereum: 'EthereumInquirer',
        original_queries: Optional[list[str]],
        extra_flags: Optional[list[str]],
        original_requests_get,
):
    eth_scan = ethereum.contracts.contract(string_to_evm_address('0x86F25b64e1Fe4C5162cDEeD5245575D32eC549db'))  # noqa: E501
    eth_multicall = ethereum.contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696'))  # noqa: E501
    original_queries = [] if original_queries is None else original_queries
    extra_flags = [] if extra_flags is None else extra_flags

    def mock_requests_get(url, *args, **kwargs):
        if 'etherscan.io/api?module=account&action=balance&address' in url:
            addr = url[67:109]
            value = eth_map[addr].get('ETH', '0')
            response = f'{{"status":"1","message":"OK","result":{value}}}'
        elif 'https://api.etherscan.io/api?module=proxy&action=eth_call&to=0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441&data=0x252dba4200000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000086f25b64e1fe4c5162cdeed5245575d32ec549db00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000084e5da1b6800000000000000000000000001471db828cfb96dcf215c57a7a6493702031ec100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000001000000000000000000000000255aa6df07540cb5d3d297f0d0d4d84cb52bc8e600000000000000000000000000000000000000000000000000000000' in url:  # noqa: E501
            # This is querying ethscan for the aave balances
            response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f371750000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
        elif 'https://api.etherscan.io/api?module=proxy&action=eth_call&to=0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9&data=0x35ea6a75000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7' in url:  # noqa: E501
            # aave lending pool status
            response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000003e80d060000000000000000000000000000000000000000000000000000038b5d0d773318cf7f0e9085000000000000000000000000000000000000000003b4c95d5d2bb343a6b392450000000000000000000000000000000000000000001edaad248f1f7bbdaff8da0000000000000000000000000000000000000000001f015a6650fa9124a311000000000000000000000000000000000000000000006238800ff08a1b7651888000000000000000000000000000000000000000000000000000000000637392830000000000000000000000003ed3b47dd13ec9a98b44e6204a523e766b225811000000000000000000000000e91d55ab2240594855abd11b3faae801fd4c4687000000000000000000000000531842cebbdd378f8ee36d171d6cc9c4fcf475ec000000000000000000000000515e87cb3fec986050f202a2bbfa362a2188bc3f0000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
        elif 'https://api.etherscan.io/api?module=proxy&action=eth_call&to=0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9&data=0x35ea6a750000000000000000000000002260fac5e5542a773aa44fbcfedf7c193bc2c599' in url:  # noqa: E501
            # This is querying aave for the status of the pool
            response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000007d00d08290420081c200000000000000000000000000000000000000000033d6d8eaa28625ea2840ba4000000000000000000000000000000000000000003471d710caeed5ae821e50400000000000000000000000000000000000000000000f487b0cec3822e8c80a60000000000000000000000000000000000000000000aa1b430cd04910319afff000000000000000000000000000000000000000000261ae07f3c498e21e01bfe00000000000000000000000000000000000000000000000000000000636f9edb0000000000000000000000009ff58f4ffb29fa2266ab25e75e2a8b350331165600000000000000000000000051b039b9afe64b78758f8ef091211b5387ea717c0000000000000000000000009c39809dec7f95f5e0713634a4d0701329b3b4d2000000000000000000000000f41e8f817e6c399d1ade102059c454093b24f35b0000000000000000000000000000000000000000000000000000000000000001"}'  # noqa: E501
        elif 'etherscan.io/api?module=account&action=balancemulti' in url:
            queried_accounts = []
            length = 72
            # process url and get the accounts
            while len(url) >= length:
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
        elif ('api.etherscan.io/api?module=account&action=txlistinternal&' in url or 'api.etherscan.io/api?module=account&action=txlist&' in url):  # noqa: E501
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
            contract = web3.eth.contract(address=ZERION_ADAPTER_ADDRESS, abi=ethereum.contracts.abi('ZERION_ADAPTER'))  # noqa: E501
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

        elif f'api.etherscan.io/api?module=proxy&action=eth_call&to={eth_multicall.address}' in url:  # noqa: E501
            web3 = Web3()
            contract = web3.eth.contract(address=eth_multicall.address, abi=eth_multicall.abi)
            if 'c2cb1040220768554cf699b0d863a3cd4324ce3' in url:
                multicall_purpose = 'ds_proxy'
            elif '2bdded18e2ca464355091266b7616956944ee7e' in url:
                multicall_purpose = 'compound_balances'
            elif '5f3b5dfeb7b28cdbd7faba78963ee202a494e2a2' in url:
                multicall_purpose = 'vecrv'
            elif '86f25b64e1fe4c5162cdeed5245575d32ec549db' in url:
                multicall_purpose = 'multibalance_query'
            else:
                raise AssertionError('Unknown multicall in mocked tests')

            if 'data=0x252dba42' in url:  # aggregate
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                # Get the multicall aggregate input data
                fn_abi = contract.functions.abi[0]
                assert fn_abi['name'] == 'aggregate', 'Abi position of multicall aggregate changed'
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))

                if multicall_purpose == 'multibalance_query':
                    contract = eth_scan
                    # Get the ethscan multibalance subcalls
                    ethscan_contract = web3.eth.contract(address=contract.address, abi=contract.abi)  # noqa: E501
                    # not really the given args, but we just want the fn abi
                    args = [next(iter(eth_map.keys())), list(eth_map.keys())]
                    scan_fn_abi = ethscan_contract._find_matching_fn_abi(
                        fn_identifier='tokensBalance',
                        args=args,
                    )
                    scan_input_types = get_abi_input_types(scan_fn_abi)
                    scan_output_types = get_abi_output_types(scan_fn_abi)
                    result_bytes = []
                    for call_entry in decoded_input[0]:
                        call_contract_address = deserialize_evm_address(call_entry[0])
                        assert call_contract_address == contract.address, 'balances multicall should only contain calls to scan contract'  # noqa: E501
                        call_data = call_entry[1]
                        scan_decoded_input = web3.codec.decode_abi(scan_input_types, call_data[4:])
                        account_address = deserialize_evm_address(scan_decoded_input[0])
                        token_values = []
                        for token_addy_str in scan_decoded_input[1]:
                            token_address = deserialize_evm_address(token_addy_str)
                            token = _get_token(token_address)
                            if token is None:
                                value = 0  # if token is missing from mapping return 0 value
                            else:
                                value = int(eth_map[account_address].get(token))
                                if value is None:
                                    value = 0  # if token is missing from mapping return 0 value
                            token_values.append(value)

                        result_bytes.append(web3.codec.encode_abi(scan_output_types, [token_values]))  # noqa: E501

                    result = '0x' + web3.codec.encode_abi(output_types, [len(result_bytes), result_bytes]).hex()  # noqa: E501
                    response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
                else:
                    # else has to be the 32 bytes for multicall balance
                    # of both veCRV and others. Return empty response
                    # all pylint ignores below due to https://github.com/PyCQA/pylint/issues/4114
                    args = [1, [b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' for x in decoded_input[0]]]  # noqa: E501
                    result = '0x' + web3.codec.encode_abi(output_types, args).hex()
                    response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'

            else:
                raise AssertionError('Unexpected etherscan multicall during tests: {url}')

        elif f'api.etherscan.io/api?module=proxy&action=eth_call&to={eth_scan.address}' in url:  # noqa: E501
            if 'ethscan' in original_queries:
                return original_requests_get(url, *args, **kwargs)

            web3 = Web3()
            contract = eth_scan
            ethscan_contract = web3.eth.contract(address=contract.address, abi=contract.abi)
            if 'data=0xdbdbb51b' in url:  # Eth balance query
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]

                fn_abi = ethscan_contract._find_matching_fn_abi(
                    fn_identifier='etherBalances',
                    args=[list(eth_map.keys())],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                args = []
                for raw_account_address in decoded_input[0]:
                    account_address = deserialize_evm_address(raw_account_address)
                    args.append(int(eth_map[account_address]['ETH']))
                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif 'data=0x06187b4f' in url:  # Multi token multiaddress balance query
                data = url.split('data=')[1]
                if '&apikey' in data:
                    data = data.split('&apikey')[0]
                # not really the given args, but we just want the fn abi
                args = [list(eth_map.keys()), list(eth_map.keys())]
                fn_abi = ethscan_contract._find_matching_fn_abi(
                    fn_identifier='tokensBalances',
                    args=args,
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                args = []
                for raw_account_address in decoded_input[0]:
                    account_address = deserialize_evm_address(raw_account_address)
                    x = []
                    for raw_token_address in decoded_input[1]:
                        token_address = deserialize_evm_address(raw_token_address)
                        value_to_add = 0
                        for given_asset, value in eth_map[account_address].items():
                            given_token = _get_token(given_asset)
                            if given_token is None:
                                # not a token
                                continue
                            if token_address != given_token.evm_address:
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
                fn_abi = ethscan_contract._find_matching_fn_abi(
                    fn_identifier='tokensBalance',
                    args=args,
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode_abi(input_types, bytes.fromhex(data[10:]))
                args = []
                account_address = deserialize_evm_address(decoded_input[0])
                x = []
                for raw_token_address in decoded_input[1]:
                    token_address = deserialize_evm_address(raw_token_address)
                    value_to_add = 0
                    for given_asset, value in eth_map[account_address].items():
                        given_token = _get_token(given_asset)
                        if given_token is None:
                            # not a token
                            continue

                        if token_address != given_token.evm_address:
                            continue
                        value_to_add = int(value)
                        break
                    args.append(value_to_add)

                result = '0x' + web3.codec.encode_abi(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif 'https://api.etherscan.io/api?module=proxy&action=eth_call&to=0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9&data=0x35ea6a75000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7' in url:  # noqa: E501
                # This is querying ethscan for the aave balances
                if 'ethscan' in original_queries:
                    return original_requests_get(url, *args, **kwargs)
                response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f370be0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
            elif 'https://api.etherscan.io/api?module=proxy&action=eth_call&to=0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9&data=0x35ea6a75000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7' in url:  # noqa: E501
                # This is querying aave for the status of the pool
                if 'ethscan' in original_queries:
                    return original_requests_get(url, *args, **kwargs)
                response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000003e80d060000000000000000000000000000000000000000000000000000038af6b55802f0e1cb76bbb2000000000000000000000000000000000000000003b458a890598cb1c935e9630000000000000000000000000000000000000000003f555421b1abbbff673b900000000000000000000000000000000000000000004949192d990ec458441edc0000000000000000000000000000000000000000008b75c1de391906a8441edc00000000000000000000000000000000000000000000000000000000636f9f470000000000000000000000003ed3b47dd13ec9a98b44e6204a523e766b225811000000000000000000000000e91d55ab2240594855abd11b3faae801fd4c4687000000000000000000000000531842cebbdd378f8ee36d171d6cc9c4fcf475ec000000000000000000000000515e87cb3fec986050f202a2bbfa362a2188bc3f0000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
            else:
                raise AssertionError(f'Unexpected etherscan call during tests: {url}')
        else:
            return original_requests_get(url, *args, **kwargs)

        return MockResponse(200, response)

    return patch.object(etherscan.session, 'get', wraps=mock_requests_get)


def mock_bitcoin_balances_query(
        btc_map: dict[BTCAddress, str],
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


def compare_account_data(expected: list[dict], got: list[dict]) -> None:
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


def get_web3_node_from_inquirer(ethereum_inquirer: 'EthereumInquirer') -> Web3Node:
    """Util function to simplify getting the testing web3 node object from an ethereum inquirer"""
    node_name = NodeName(
        name='own',
        endpoint='bla',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    return ethereum_inquirer.web3_mapping[node_name]


def set_web3_node_in_inquirer(ethereum_inquirer: 'EthereumInquirer', web3node: Web3Node) -> None:
    """Util function to simplify setting the testing web3 node object from an ethereum inquirer"""
    node_name = NodeName(
        name='own',
        endpoint='bla',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    ethereum_inquirer.web3_mapping[node_name] = web3node


def setup_evm_addresses_activity_mock(
        stack: 'ExitStack',
        chains_aggregator: 'ChainsAggregator',
        eth_contract_addresses: list[ChecksumEvmAddress],
        ethereum_addresses: list[ChecksumEvmAddress],
        avalanche_addresses: Optional[list[ChecksumEvmAddress]] = None,
        optimism_addresses: Optional[list[ChecksumEvmAddress]] = None,
        polygon_pos_addresses: Optional[list[ChecksumEvmAddress]] = None,
        arbitrum_one_addresses: Optional[list[ChecksumEvmAddress]] = None,
) -> 'ExitStack':
    def mock_ethereum_get_code(account):
        if account in eth_contract_addresses:
            return '0xsomecode'
        return '0x'

    def mock_avax_get_tx_count(account):
        if account in avalanche_addresses:
            return 1
        return 0

    def mock_avax_balance(account):
        if account in avalanche_addresses:
            return FVal(1)
        return ZERO

    def mock_optimism_has_activity(account):
        if account in optimism_addresses:
            return EtherscanHasChainActivity.TRANSACTIONS
        return EtherscanHasChainActivity.NONE

    def mock_polygon_pos_has_activity(account):
        if account in polygon_pos_addresses:
            return EtherscanHasChainActivity.TRANSACTIONS
        return EtherscanHasChainActivity.NONE

    def mock_ethereum_has_activity(account):
        if account in ethereum_addresses:
            return EtherscanHasChainActivity.TRANSACTIONS
        return EtherscanHasChainActivity.NONE

    def mock_arbitrum_one_has_activity(account):
        if account in arbitrum_one_addresses:
            return EtherscanHasChainActivity.TRANSACTIONS
        return EtherscanHasChainActivity.NONE

    stack.enter_context(patch.object(
        chains_aggregator.ethereum.node_inquirer,
        'get_code',
        side_effect=mock_ethereum_get_code,
    ))
    stack.enter_context(patch.object(
        chains_aggregator.avalanche.w3.eth,
        'get_transaction_count',
        side_effect=mock_avax_get_tx_count,
    ))
    stack.enter_context(patch.object(
        chains_aggregator.avalanche,
        'get_avax_balance',
        side_effect=mock_avax_balance,
    ))
    stack.enter_context(patch.object(
        chains_aggregator.optimism.node_inquirer.etherscan,
        'has_activity',
        side_effect=mock_optimism_has_activity,
    ))
    stack.enter_context(patch.object(
        chains_aggregator.polygon_pos.node_inquirer.etherscan,
        'has_activity',
        side_effect=mock_polygon_pos_has_activity,
    ))
    stack.enter_context(patch.object(
        chains_aggregator.ethereum.node_inquirer.etherscan,
        'has_activity',
        side_effect=mock_ethereum_has_activity,
    ))
    stack.enter_context(patch.object(
        chains_aggregator.arbitrum_one.node_inquirer.etherscan,
        'has_activity',
        side_effect=mock_arbitrum_one_has_activity,
    ))
    return stack


def maybe_modify_rpc_nodes(
        database: 'DBHandler',
        blockchain: SupportedBlockchain,
        manager_connect_at_start: Union[str, Sequence['WeightedNode']],
) -> Sequence['WeightedNode']:
    """Modify the rpc nodes in the DB for the given blockchain depending on
    the value of the managager_connect_at_start.

    IF it's a string can only be default. In which case we get the nodes
    to connect to directly as default from the DB.

    But if it's a tuple of entries we clean the DB except the etherscan entry
    and write that tuple. Tuple may also be empty which results in clean all nodes
    except etherscan for the chain.

    Returns the nodes to connect to.
    """
    if isinstance(manager_connect_at_start, str):
        assert manager_connect_at_start == 'DEFAULT'
        nodes_to_connect_to = database.get_rpc_nodes(blockchain, only_active=True)
    else:
        nodes_to_connect_to = manager_connect_at_start
        with database.user_write() as write_cursor:
            write_cursor.execute(  # Delete all but etherscan endpoint
                'DELETE FROM rpc_nodes WHERE blockchain=? and endpoint!=""',
                (blockchain.value,))
        for entry in nodes_to_connect_to:
            if entry.node_info.endpoint != '':  # don't re-add etherscan
                database.add_rpc_node(entry)

    return nodes_to_connect_to
