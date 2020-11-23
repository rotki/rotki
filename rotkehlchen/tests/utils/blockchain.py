import json
import logging
import os
import shutil
import subprocess
from binascii import hexlify
from typing import Any, Dict, List, Optional, Union
from unittest.mock import patch

import gevent
from eth_utils.address import to_checksum_address
from web3 import Web3
from web3._utils.abi import get_abi_input_types, get_abi_output_types
from web3.middleware import geth_poa_middleware

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.manager import NodeName
from rotkehlchen.chain.ethereum.zerion import ZERION_ADAPTER_ADDRESS
from rotkehlchen.constants.ethereum import ETH_SCAN, ZERION_ABI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.crypto import address_encoder, privatekey_to_address
from rotkehlchen.errors import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.fval import FVal
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.eth_tokens import CONTRACT_ADDRESS_TO_TOKEN
from rotkehlchen.tests.utils.genesis import GENESIS_STUB
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import BTCAddress, ChecksumEthAddress
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc

logger = logging.getLogger(__name__)

DEFAULT_BALANCE = (10 ** 18) * 1000000
DEFAULT_BALANCE_BIN = str(DEFAULT_BALANCE)


def clique_extradata(extra_vanity, extra_seal):
    if len(extra_vanity) > 64:
        raise ValueError('extra_vanity length must be smaller-or-equal to 64')

    # Format is determined by the clique PoA:
    # https://github.com/ethereum/EIPs/issues/225
    # - First EXTRA_VANITY bytes (fixed) may contain arbitrary signer vanity data
    # - Last EXTRA_SEAL bytes (fixed) is the signer's signature sealing the header
    return '0x{:0<64}{:0<170}'.format(
        extra_vanity,
        extra_seal,
    )


def geth_bare_genesis(genesis_path, private_keys, random_marker):
    """Writes a bare genesis to `genesis_path`.

    Args:
        genesis_path (str): the path in which the genesis block is written.
        private_keys list(str): iterable list of privatekeys whose corresponding accounts will
                    have a premined balance available.
    """

    account_addresses = [
        privatekey_to_address(key)
        for key in sorted(set(private_keys))
    ]

    alloc = {
        address_encoder(address): {
            'balance': DEFAULT_BALANCE_BIN,
        }
        for address in account_addresses
    }
    genesis = GENESIS_STUB.copy()
    genesis['alloc'].update(alloc)

    genesis['config']['clique'] = {'period': 1, 'epoch': 30000}

    genesis['extraData'] = clique_extradata(
        random_marker,
        address_encoder(account_addresses[0])[2:],
    )

    with open(genesis_path, 'w') as handler:
        json.dump(genesis, handler)


def geth_init_datadir(datadir, genesis_path):
    """Initialize a clients datadir with our custom genesis block.

    Args:
        datadir (str): the datadir in which the blockchain is initialized.
    """
    try:
        args = [
            'geth',
            '--datadir',
            datadir,
            'init',
            genesis_path,
        ]
        subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        msg = 'Initializing geth with custom genesis returned {} with error:\n {}'.format(
            e.returncode,
            e.output,
        )
        raise ValueError(msg)


def geth_to_cmd(port, rpcport, datadir, verbosity):
    """Prepare a get command with the specified arguments"""

    cmd = ['geth']
    # dont use the '--dev' flag
    cmd.extend([
        '--nodiscover',
        '--ipcdisable',
        '--rpc',
        '--rpcapi', 'eth,net,web3',
        '--rpcaddr', '0.0.0.0',
        '--networkid', '637',
        '--port', str(port),
        '--rpcport', str(rpcport),
        '--minerthreads', '1',
        '--verbosity', str(verbosity),
        '--datadir', datadir,
    ])

    logger.debug('geth command: {}'.format(cmd))

    return cmd


def geth_wait_and_check(ethereum_manager, rpc_endpoint, random_marker):
    """ Wait until the geth cluster is ready. """
    jsonrpc_running = False

    tries = 5
    while not jsonrpc_running and tries > 0:
        success, _ = ethereum_manager.attempt_connect(
            name=NodeName.OWN,
            ethrpc_endpoint=rpc_endpoint,
            mainnet_check=False,
        )
        if not success:
            gevent.sleep(0.5)
            tries -= 1
        else:
            # inject the web3 middleware for PoA to not fail at extraData validation
            # https://github.com/ethereum/web3.py/issues/549
            web3 = ethereum_manager.web3_mapping[NodeName.OWN]
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            jsonrpc_running = True
            block = ethereum_manager.get_block_by_number(0)
            running_marker = hexlify(block['proofOfAuthorityData'])[:len(random_marker)].decode()
            if running_marker != random_marker:
                raise RuntimeError(
                    'the test marker does not match, maybe two tests are running in '
                    'parallel with the same port?',
                )

    if jsonrpc_running is False:
        raise ValueError('geth didnt start the jsonrpc interface')


def geth_create_blockchain(
        ethereum_manager,
        private_keys,
        gethport,
        gethrpcendpoint,
        gethrpcport,
        base_datadir,
        verbosity,
        random_marker,
        genesis_path=None,
        logdirectory=None,
):
    nodekey_part = 'foo'  # since we have only 1 instance running any string is fine
    nodedir = os.path.join(base_datadir, nodekey_part)
    node_genesis_path = os.path.join(nodedir, 'custom_genesis.json')

    assert len(nodedir + '/geth.ipc') <= 104, (
        f'geth data path is too large: {nodedir}'
    )

    os.makedirs(nodedir)

    if genesis_path is None:
        geth_bare_genesis(node_genesis_path, private_keys, random_marker)
    else:
        shutil.copy(genesis_path, node_genesis_path)

    geth_init_datadir(nodedir, node_genesis_path)

    cmd = geth_to_cmd(gethport, gethrpcport, nodedir, verbosity)

    stdout = None
    stderr = None

    if logdirectory:
        log_path = os.path.join(logdirectory, 'gethlog')
        logfile = open(log_path, 'w')
        stdout = logfile
        stderr = logfile

    process = subprocess.Popen(
        cmd,
        universal_newlines=True,
        stdout=stdout,
        stderr=stderr,
    )

    try:
        geth_wait_and_check(ethereum_manager, gethrpcendpoint, random_marker)
    except (ValueError, RuntimeError, KeyError) as e:
        # if something goes wrong in the above function make sure to kill the geth
        # process before quitting the tests
        process.terminate()
        raise e

    process.poll()

    if process.returncode is not None:
        raise ValueError('geth failed to start')

    return process


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

    # Check our owned eth tokens here since the test may have changed their number
    owned_assets = set(rotki.chain_manager.totals.assets.keys())
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
        except DeserializationError:
            # not a token
            return None
        return token
    elif value.asset_type == AssetType.ETH_TOKEN:
        return value

    return None


def mock_etherscan_query(
        eth_map: Dict[ChecksumEthAddress, Dict[Union[str, EthereumToken], Any]],
        etherscan: Etherscan,
        original_queries: Optional[List[str]],
        original_requests_get,
):
    original_queries = [] if original_queries is None else original_queries

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
            # By default when mocking, don't query for transactions
            response = '{"status":"1","message":"OK","result":[]}'
        elif 'api.etherscan.io/api?module=account&action=txlist&' in url:
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
            else:
                raise AssertionError(f'Unexpected etherscan call during tests: {url}')
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
                for account_address in decoded_input[0]:
                    account_address = to_checksum_address(account_address)
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
                for account_address in decoded_input[0]:
                    account_address = to_checksum_address(account_address)
                    x = []
                    for token_address in decoded_input[1]:
                        token_address = to_checksum_address(token_address)
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
                account_address = to_checksum_address(decoded_input[0])
                x = []
                for token_address in decoded_input[1]:
                    token_address = to_checksum_address(token_address)
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

    return patch('rotkehlchen.utils.misc.requests.get', wraps=mock_requests_get)


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
