import json
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final
from unittest.mock import patch

from eth_utils.abi import get_abi_input_types, get_abi_output_types
from web3 import Web3

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZERION_ADAPTER_ADDRESS
from rotkehlchen.chain.evm.constants import BALANCE_SCANNER_ADDRESS
from rotkehlchen.chain.evm.types import NodeName, string_to_evm_address
from rotkehlchen.chain.mixins.rpc_nodes import RPCNode
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL, ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.externalapis.etherscan import Etherscan, HasChainActivity
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tests.utils.eth_tokens import CONTRACT_ADDRESS_TO_TOKEN
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    BTCAddress,
    ChainID,
    ChecksumEvmAddress,
    SupportedBlockchain,
)
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc

if TYPE_CHECKING:
    from contextlib import ExitStack

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.db.dbhandler import DBHandler

ETHERSCAN_API_URL: Final = 'https://api.etherscan.io/v2/api'


def assert_btc_balances_result(
        result: dict[str, Any],
        btc_accounts: list['BTCAddress'],
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
    assert FVal(totals['BTC'][DEFAULT_BALANCE_LABEL]['amount']) == expected_btc_total
    if expected_btc_total == ZERO:
        assert FVal(totals['BTC'][DEFAULT_BALANCE_LABEL]['usd_value']) == ZERO
    else:
        assert FVal(totals['BTC'][DEFAULT_BALANCE_LABEL]['usd_value']) > ZERO


def assert_eth_balances_result(
        rotki: Rotkehlchen,
        result: dict[str, Any],
        eth_accounts: list['ChecksumEvmAddress'],
        eth_balances: list[str],
        token_balances: dict[EvmToken, list[str]],
        also_btc: bool,
        expected_liabilities: dict[EvmToken, list[str]] | None = None,
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
            amount = FVal(per_account[account]['assets'][A_ETH.identifier][DEFAULT_BALANCE_LABEL]['amount'])  # noqa: E501
            usd_value = FVal(per_account[account]['assets'][A_ETH.identifier][DEFAULT_BALANCE_LABEL]['usd_value'])  # noqa: E501
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
                    token_amount = FVal(per_account[account]['assets'][token.identifier][DEFAULT_BALANCE_LABEL]['amount'])  # noqa: E501
                    usd_value = FVal(
                        per_account[account]['assets'][token.identifier][DEFAULT_BALANCE_LABEL]['usd_value'],
                    )
                    assert token_amount == from_wei(expected_token_amount)

    if totals_only:
        totals = result
    else:
        totals = result['totals']['assets']

    if expected_liabilities is not None:
        per_account = result['per_account'][SupportedBlockchain.ETHEREUM.serialize()]
        for token, balances in expected_liabilities.items():
            total_amount = ZERO
            for idx, account in enumerate(eth_accounts):
                amount = FVal(per_account[account]['liabilities'][token.identifier][DEFAULT_BALANCE_LABEL]['amount'])  # noqa: E501
                assert amount == FVal(balances[idx])
                total_amount += amount

            assert FVal(result['totals']['liabilities'][token.identifier][DEFAULT_BALANCE_LABEL]['amount']) == total_amount  # noqa: E501

    # Check our owned eth tokens here since the test may have changed their number
    owned_assets = set(rotki.chains_aggregator.totals.assets.keys())
    if not also_btc:
        owned_assets.discard(A_BTC)
    assert len(totals) == len(owned_assets)

    expected_total_eth = sum(from_wei(FVal(balance)) for balance in eth_balances)
    assert FVal(totals[A_ETH.identifier][DEFAULT_BALANCE_LABEL]['amount']) == expected_total_eth
    for token, balances in token_balances.items():
        symbol = token.identifier

        expected_total_token = sum(from_wei(FVal(balance)) for balance in balances)
        assert FVal(totals[symbol][DEFAULT_BALANCE_LABEL]['amount']) == expected_total_token


def _get_token(value: Any) -> EvmToken | None:
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
        original_queries: list[str] | None,
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

    return patch.object(beaconchain.session, 'request', wraps=mock_requests_get)


def mock_etherscan_query(
        eth_map: dict[ChecksumEvmAddress, dict[str | EvmToken, Any]],
        etherscan: Etherscan,
        ethereum: 'EthereumInquirer',
        original_queries: list[str] | None,
        extra_flags: list[str] | None,
        original_requests_get,
):
    eth_scan = ethereum.contracts.contract(BALANCE_SCANNER_ADDRESS)
    eth_multicall = ethereum.contracts.contract(string_to_evm_address('0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696'))  # noqa: E501
    original_queries = [] if original_queries is None else original_queries
    extra_flags = [] if extra_flags is None else extra_flags

    def mock_requests_get(url, params, *args, **kwargs):

        def check_params(
                values: dict[str, str] | None = None,
                keys: list[str] | None = None,
        ) -> bool:
            if url != ETHERSCAN_API_URL:
                return False

            if values is not None:
                for key, value in values.items():
                    if params.get(key) != value:
                        return False

            if keys is not None:
                for key in keys:
                    if key not in params:
                        return False

            return True

        if check_params(values={'module': 'account', 'action': 'balance'}, keys=['address']):
            addr = url[67:109]
            value = eth_map[addr].get('ETH', '0')
            response = f'{{"status":"1","message":"OK","result":{value}}}'
        elif check_params(values={'module': 'proxy', 'action': 'eth_call', 'to': '0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441', 'data': '0x252dba4200000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000086f25b64e1fe4c5162cdeed5245575d32ec549db00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000084e5da1b6800000000000000000000000001471db828cfb96dcf215c57a7a6493702031ec100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000001000000000000000000000000255aa6df07540cb5d3d297f0d0d4d84cb52bc8e600000000000000000000000000000000000000000000000000000000'}):   # noqa: E501
            # This is querying ethscan for the aave balances
            response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f371750000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
        elif check_params(values={'module': 'proxy', 'action': 'eth_call', 'to': '0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9', 'data': '0x35ea6a75000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7'}):  # noqa: E501
            # aave lending pool status
            response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000003e80d060000000000000000000000000000000000000000000000000000038b5d0d773318cf7f0e9085000000000000000000000000000000000000000003b4c95d5d2bb343a6b392450000000000000000000000000000000000000000001edaad248f1f7bbdaff8da0000000000000000000000000000000000000000001f015a6650fa9124a311000000000000000000000000000000000000000000006238800ff08a1b7651888000000000000000000000000000000000000000000000000000000000637392830000000000000000000000003ed3b47dd13ec9a98b44e6204a523e766b225811000000000000000000000000e91d55ab2240594855abd11b3faae801fd4c4687000000000000000000000000531842cebbdd378f8ee36d171d6cc9c4fcf475ec000000000000000000000000515e87cb3fec986050f202a2bbfa362a2188bc3f0000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
        elif check_params(values={'module': 'proxy', 'action': 'eth_call', 'to': '0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9', 'data': '0x35ea6a750000000000000000000000002260fac5e5542a773aa44fbcfedf7c193bc2c599'}):  # noqa: E501
            # This is querying aave for the status of the pool
            response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000007d00d08290420081c200000000000000000000000000000000000000000033d6d8eaa28625ea2840ba4000000000000000000000000000000000000000003471d710caeed5ae821e50400000000000000000000000000000000000000000000f487b0cec3822e8c80a60000000000000000000000000000000000000000000aa1b430cd04910319afff000000000000000000000000000000000000000000261ae07f3c498e21e01bfe00000000000000000000000000000000000000000000000000000000636f9edb0000000000000000000000009ff58f4ffb29fa2266ab25e75e2a8b350331165600000000000000000000000051b039b9afe64b78758f8ef091211b5387ea717c0000000000000000000000009c39809dec7f95f5e0713634a4d0701329b3b4d2000000000000000000000000f41e8f817e6c399d1ade102059c454093b24f35b0000000000000000000000000000000000000000000000000000000000000001"}'  # noqa: E501
        elif check_params(values={'module': 'account', 'action': 'balancemulti'}):
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

        elif check_params(values={'module': 'account', 'action': 'tokenbalance'}):
            token_address = url[80:122]
            msg = 'token address missing from test mapping'
            assert token_address in CONTRACT_ADDRESS_TO_TOKEN, msg
            response = '{"status":"1","message":"OK","result":"0"}'
            token = CONTRACT_ADDRESS_TO_TOKEN[token_address]
            account = url[131:173]
            value = eth_map[account].get(token.identifier, 0)
            response = f'{{"status":"1","message":"OK","result":"{value}"}}'
        elif (
            check_params(values={'module': 'account', 'action': 'txlistinternal'}) or
            check_params(values={'module': 'account', 'action': 'txlist'})
        ):
            if 'transactions' in original_queries:
                return original_requests_get(url, params, *args, **kwargs)
            # By default when mocking, don't query for transactions
            response = '{"status":"1","message":"OK","result":[]}'
        elif check_params(values={'module': 'logs', 'action': 'getLogs'}):
            if 'logs' in original_queries:
                return original_requests_get(url, params, *args, **kwargs)
            # By default when mocking, don't query logs
            response = '{"status":"1","message":"OK","result":[]}'
        elif check_params(values={'module': 'block', 'action': 'getblocknobytime'}):
            if 'blocknobytime' in original_queries:
                return original_requests_get(url, params, *args, **kwargs)
            # By default when mocking don't query blocknobytime
            response = '{"status":"1","message":"OK","result":"1"}'
        elif check_params(values={'module': 'proxy', 'action': 'eth_call', 'to': ZERION_ADAPTER_ADDRESS}):  # noqa: E501
            if 'zerion' in original_queries:
                return original_requests_get(url, params, *args, **kwargs)

            web3 = Web3()
            contract = web3.eth.contract(address=ZERION_ADAPTER_ADDRESS, abi=ethereum.contracts.abi('ZERION_ADAPTER'))  # noqa: E501
            data = params.get('data') or ''
            if data.startswith('0xc84aae17'):  # getBalances
                fn_abi = contract._find_matching_fn_abi(
                    'getBalances',
                    *['address'],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))
                # TODO: This here always returns empty response. If/when we want to
                # mock it for etherscan, this is where we do it
                args = []
                result = '0x' + web3.codec.encode(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif data.startswith('0x85c6a7930'):  # getProtocolBalances
                fn_abi = contract._find_matching_fn_abi(
                    'getProtocolBalances',
                    *['address', ['some', 'protocol', 'names']],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))
                # TODO: This here always returns empty response. If/when we want to
                # mock it for etherscan, this is where we do it
                args = []
                result = '0x' + web3.codec.encode(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif data.startswith('0x3b692f52'):  # getProtocolNames
                fn_abi = contract._find_matching_fn_abi('getProtocolNames')
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))
                # TODO: This here always returns empty response. If/when we want to
                # mock it for etherscan, this is where we do it
                args = []
                result = '0x' + web3.codec.encode(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            else:
                raise AssertionError(f'Unexpected etherscan call during tests: {url}')

        elif check_params(values={'module': 'proxy', 'action': 'eth_call', 'to': eth_multicall.address}):  # noqa: E501
            web3 = Web3()
            contract = web3.eth.contract(address=eth_multicall.address, abi=eth_multicall.abi)
            data = params.get('data') or ''
            if (
                    'c2cb1040220768554cf699b0d863a3cd4324ce3' in data or  # DSProxy
                    '4678f0a6958e4d2bc4f1baf7bc52e8f3564f3fe4' in data or  # Sky Proxy
                    '807def5e7d057df05c796f4bc75c3fe82bd6eee1' in data  # liquity router (for proxies)  # noqa: E501
            ):
                multicall_purpose = 'proxy'
            elif '2bdded18e2ca464355091266b7616956944ee7e' in data:
                multicall_purpose = 'compound_balances'
            elif '5f3b5dfeb7b28cdbd7faba78963ee202a494e2a2' in data:
                multicall_purpose = 'vecrv'
            elif '54ecf3f6f61f63fdfe7c27ee8a86e54899600c92' in data:
                multicall_purpose = 'multibalance_query'
            else:
                raise AssertionError('Unknown multicall in mocked tests')

            if '54ecf3f6f61f63fdfe7c27ee8a86e54899600c92' in data:
                # can appear mixed with above so multibalance can trump the rest since actionable
                multicall_purpose = 'multibalance_query'

            if data.startswith('0x252dba42'):  # aggregate
                # Get the multicall aggregate input data
                fn_abi = contract.functions.abi[0]
                assert fn_abi['name'] == 'aggregate', 'Abi position of multicall aggregate changed'
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))

                if multicall_purpose == 'multibalance_query':
                    contract = eth_scan
                    # Get the ethscan multibalance subcalls
                    ethscan_contract = web3.eth.contract(address=contract.address, abi=contract.abi)  # noqa: E501
                    # not really the given args, but we just want the fn abi
                    args = [next(iter(eth_map.keys())), list(eth_map.keys())]
                    scan_fn_abi = ethscan_contract._find_matching_fn_abi(
                        'tokens_balance',
                        *args,
                    )
                    scan_input_types = get_abi_input_types(scan_fn_abi)
                    scan_output_types = get_abi_output_types(scan_fn_abi)
                    result_bytes = []
                    for call_entry in decoded_input[0]:
                        call_contract_address = deserialize_evm_address(call_entry[0])
                        assert call_contract_address == contract.address, 'balances multicall should only contain calls to scan contract'  # noqa: E501
                        call_data = call_entry[1]
                        scan_decoded_input = web3.codec.decode(scan_input_types, call_data[4:])
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

                        result_bytes.append(web3.codec.encode(scan_output_types, [token_values]))

                    result = '0x' + web3.codec.encode(output_types, [len(result_bytes), result_bytes]).hex()  # noqa: E501
                    response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
                else:
                    # else has to be the 32 bytes for multicall balance
                    # of both veCRV and others. Return empty response
                    # all pylint ignores below due to https://github.com/PyCQA/pylint/issues/4114
                    args = [1, [b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' for x in decoded_input[0]]]  # noqa: E501
                    result = '0x' + web3.codec.encode(output_types, args).hex()
                    response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'

            else:
                raise AssertionError(f'Unexpected etherscan multicall during tests: {url}')

        elif check_params(values={'module': 'proxy', 'action': 'eth_call', 'to': eth_scan.address}):  # noqa: E501
            if 'ethscan' in original_queries:
                return original_requests_get(url, params, *args, **kwargs)

            web3 = Web3()
            contract = eth_scan
            ethscan_contract = web3.eth.contract(address=contract.address, abi=contract.abi)
            data = params.get('data') or ''
            if data.startswith('0xee1806d2'):  # Eth balance query
                fn_abi = ethscan_contract._find_matching_fn_abi(
                    'ether_balances',
                    *[list(eth_map.keys())],
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))
                args = []
                for raw_account_address in decoded_input[0]:
                    account_address = deserialize_evm_address(raw_account_address)
                    args.append(int(eth_map[account_address]['ETH']))
                result = '0x' + web3.codec.encode(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif data.startswith('0x665bb79e'):  # Multi token multiaddress balance query
                # not really the given args, but we just want the fn abi
                args = [list(eth_map.keys()), list(eth_map.keys())]
                fn_abi = ethscan_contract._find_matching_fn_abi(
                    fn_identifier='tokens_balances',
                    args=args,
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))
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

                result = '0x' + web3.codec.encode(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'

            elif data.startswith('0xb0d861b8'):  # Multi token balance query
                # not really the given args, but we just want the fn abi
                args = ['str', list(eth_map.keys())]
                fn_abi = ethscan_contract._find_matching_fn_abi(
                    'tokens_balance',
                    *args,
                )
                input_types = get_abi_input_types(fn_abi)
                output_types = get_abi_output_types(fn_abi)
                decoded_input = web3.codec.decode(input_types, bytes.fromhex(data[10:]))
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

                result = '0x' + web3.codec.encode(output_types, [args]).hex()
                response = f'{{"jsonrpc":"2.0","id":1,"result":"{result}"}}'
            elif data == '0x35ea6a75000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7':  # noqa: E501
                # This is querying ethscan for the aave balances
                if 'ethscan' in original_queries:
                    return original_requests_get(url, params, *args, **kwargs)
                response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f370be0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
            elif data == '0x35ea6a75000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7':  # noqa: E501
                # This is querying aave for the status of the pool
                if 'ethscan' in original_queries:
                    return original_requests_get(url, params, *args, **kwargs)
                response = '{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000003e80d060000000000000000000000000000000000000000000000000000038af6b55802f0e1cb76bbb2000000000000000000000000000000000000000003b458a890598cb1c935e9630000000000000000000000000000000000000000003f555421b1abbbff673b900000000000000000000000000000000000000000004949192d990ec458441edc0000000000000000000000000000000000000000008b75c1de391906a8441edc00000000000000000000000000000000000000000000000000000000636f9f470000000000000000000000003ed3b47dd13ec9a98b44e6204a523e766b225811000000000000000000000000e91d55ab2240594855abd11b3faae801fd4c4687000000000000000000000000531842cebbdd378f8ee36d171d6cc9c4fcf475ec000000000000000000000000515e87cb3fec986050f202a2bbfa362a2188bc3f0000000000000000000000000000000000000000000000000000000000000000"}'  # noqa: E501
            else:
                raise AssertionError(f'Unexpected etherscan call during tests: {url}')
        else:
            return original_requests_get(url, params, *args, **kwargs)

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


def get_web3_node_from_inquirer(ethereum_inquirer: 'EthereumInquirer') -> RPCNode:
    """Util function to simplify getting the testing web3 node object from an ethereum inquirer"""
    node_name = NodeName(
        name='own',
        endpoint='bla',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    return ethereum_inquirer.rpc_mapping[node_name]


def set_web3_node_in_inquirer(ethereum_inquirer: 'EthereumInquirer', rpc_node: RPCNode) -> None:
    """Util function to simplify setting the testing web3 node object from an ethereum inquirer"""
    node_name = NodeName(
        name='own',
        endpoint='bla',
        owned=True,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    ethereum_inquirer.rpc_mapping[node_name] = rpc_node


def setup_evm_addresses_activity_mock(
        stack: 'ExitStack',
        chains_aggregator: 'ChainsAggregator',
        eth_contract_addresses: list[ChecksumEvmAddress],
        ethereum_addresses: list[ChecksumEvmAddress],  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        avalanche_addresses: list[ChecksumEvmAddress] | None = None,
        optimism_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        polygon_pos_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        arbitrum_one_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        base_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        gnosis_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        scroll_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        binance_sc_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
        zksync_lite_addresses: list[ChecksumEvmAddress] | None = None,  # pylint: disable=unused-argument  # used by the saved locals  # noqa: E501, RUF100
) -> 'ExitStack':
    saved_locals = locals()  # bit hacky, but save locals here so they can be accessed by mock_chain_has_activity  # noqa: E501

    def mock_ethereum_get_code(account):
        if account in eth_contract_addresses:
            return '0xsomecode'
        return '0x'

    def mock_is_safe_or_eoa(address: ChecksumEvmAddress, chain: SupportedBlockchain):
        return address not in eth_contract_addresses

    def mock_avax_get_tx_count(account):
        if account in avalanche_addresses:
            return 1
        return 0

    def mock_avax_balance(account):
        if account in avalanche_addresses:
            return ONE
        return ZERO

    def mock_zksync_lite_query_api(url, options):  # pylint: disable=unused-argument
        re_match = re.search(r'accounts\/(0x[a-fA-F0-9]{40})\/transactions', url)
        assert re_match, f'Unexpected zksync lite url: {url}'
        address = re_match.group(1)
        if zksync_lite_addresses and address in zksync_lite_addresses:
            return {'list': [1, 2]}  # a list with non zero length -- exists
        return {}  # does not exist

    def mock_chain_has_activity(chain: ChainID | SupportedBlockchain, account: ChecksumEvmAddress):
        name = chain.to_name() if isinstance(chain, ChainID) else chain.to_chain_id().to_name()
        addresses = saved_locals[f'{name}_addresses']
        return HasChainActivity.TRANSACTIONS if addresses is not None and account in addresses else HasChainActivity.NONE  # noqa: E501

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
        chains_aggregator.zksync_lite,
        '_query_api',
        side_effect=mock_zksync_lite_query_api,
    ))
    stack.enter_context(patch.object(
        chains_aggregator,
        'is_safe_proxy_or_eoa',
        side_effect=mock_is_safe_or_eoa,
    ))

    for chain in EVM_CHAINS_WITH_TRANSACTIONS:
        manager = chains_aggregator.get_evm_manager(as_chain_id := chain.to_chain_id())
        stack.enter_context(patch.object(
            manager.node_inquirer.etherscan,
            'has_activity',
            side_effect=lambda chain_id, account: mock_chain_has_activity(chain_id, account),  # noqa: PLW0108
        ))
        if manager.node_inquirer.blockscout is not None:
            stack.enter_context(patch.object(
                manager.node_inquirer.blockscout,
                'has_activity',
                side_effect=lambda account, i_chain=chain: mock_chain_has_activity(i_chain, account),  # noqa: E501
            ))

    return stack


def maybe_modify_rpc_nodes(
        database: 'DBHandler',
        blockchain: SupportedBlockchain,
        manager_connect_at_start: str | Sequence['WeightedNode'],
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
                "DELETE FROM rpc_nodes WHERE blockchain=? and endpoint!=''",
                (blockchain.value,))
        for entry in nodes_to_connect_to:
            if entry.node_info.endpoint != '':  # don't re-add etherscan
                database.add_rpc_node(entry)

    return nodes_to_connect_to
