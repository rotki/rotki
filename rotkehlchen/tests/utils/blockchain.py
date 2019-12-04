import io
import json
import logging
import os
import shutil
import subprocess
import sys
from binascii import hexlify
from typing import Any, Dict, List
from unittest.mock import patch

import gevent
from web3.middleware import geth_poa_middleware

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.crypto import address_encoder, privatekey_to_address
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.genesis import GENESIS_STUB
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc

if os.name != 'nt':
    # termios does not exist in windows
    import termios


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


def geth_wait_and_check(ethchain_client, rpc_endpoint, random_marker):
    """ Wait until the geth cluster is ready. """
    jsonrpc_running = False

    tries = 5
    while not jsonrpc_running and tries > 0:
        success, _ = ethchain_client.attempt_connect(rpc_endpoint, mainnet_check=False)
        if not success:
            gevent.sleep(0.5)
            tries -= 1
        else:
            # inject the web3 middleware for PoA to not fail at extraData validation
            # https://github.com/ethereum/web3.py/issues/549
            ethchain_client.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            jsonrpc_running = True
            block = ethchain_client.get_block_by_number(0)
            running_marker = hexlify(block['proofOfAuthorityData'])[:24].decode()
            if running_marker != random_marker:
                raise RuntimeError(
                    'the test marker does not match, maybe two tests are running in '
                    'parallel with the same port?',
                )

    if jsonrpc_running is False:
        raise ValueError('geth didnt start the jsonrpc interface')


def geth_create_blockchain(
        ethchain_client,
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

    # save current term settings before running geth
    # check that the test is running on non-capture mode
    if os.name != 'nt' and isinstance(sys.stdin, io.IOBase):
        term_settings = termios.tcgetattr(sys.stdin)

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
        geth_wait_and_check(ethchain_client, gethrpcendpoint, random_marker)
    except (ValueError, RuntimeError, KeyError) as e:
        # if something goes wrong in the above function make sure to kill the geth
        # process before quitting the tests
        process.terminate()
        raise e
    finally:
        # reenter echo mode (disabled by geth pasphrase prompt)
        if os.name != 'nt' and isinstance(sys.stdin, io.IOBase):
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, term_settings)

    process.poll()

    if process.returncode is not None:
        raise ValueError('geth failed to start')

    return process


def assert_btc_balances_result(
        json_data: Dict[str, Any],
        btc_balances: List[str],
        also_eth: bool,
) -> None:
    """Asserts for correct BTC blockchain balances when mocked in tests"""
    btc_balance1 = btc_balances[0]
    btc_balance2 = btc_balances[1]
    result = json_data['result']
    per_account = result['per_account']
    if also_eth:
        assert len(per_account) == 2
    else:
        assert len(per_account) == 1
    per_account = per_account['BTC']
    assert len(per_account) == 2
    assert FVal(per_account[UNIT_BTC_ADDRESS1]['amount']) == satoshis_to_btc(
        FVal(btc_balance1),
    )
    assert FVal(per_account[UNIT_BTC_ADDRESS1]['usd_value']) > ZERO
    assert FVal(per_account[UNIT_BTC_ADDRESS2]['amount']) == satoshis_to_btc(
        FVal(btc_balance2),
    )
    assert FVal(per_account[UNIT_BTC_ADDRESS2]['usd_value']) > ZERO

    totals = result['totals']
    if also_eth:
        assert len(totals) == 3
    else:
        assert len(totals) == 1

    assert FVal(totals['BTC']['amount']) == (
        satoshis_to_btc(FVal(btc_balance1)) +
        satoshis_to_btc(FVal(btc_balance2))
    )
    assert FVal(totals['BTC']['usd_value']) > ZERO


def assert_eth_balances_result(
        json_data: Dict[str, Any],
        eth_accounts: List[str],
        eth_balances: List[str],
        rdn_balance: str,
        also_btc: bool,
        totals_only: bool = False
) -> None:
    """Asserts for correct ETH blockchain balances when mocked in tests

    If totals_only is given then this is a query for all balances so only the totals are shown
    """
    eth_acc1 = eth_accounts[0]
    eth_acc2 = eth_accounts[1]
    eth_balance1 = eth_balances[0]
    eth_balance2 = eth_balances[1]
    result = json_data['result']
    if not totals_only:
        per_account = result['per_account']
        if also_btc:
            assert len(per_account) == 2
        else:
            assert len(per_account) == 1
        per_account = per_account['ETH']
        assert len(per_account) == 2
        assert FVal(per_account[eth_acc1]['ETH']) == from_wei(FVal(eth_balance1))
        assert FVal(per_account[eth_acc1]['usd_value']) > ZERO
        assert FVal(per_account[eth_acc2]['ETH']) == from_wei(FVal(eth_balance2))
        assert FVal(per_account[eth_acc2]['RDN']) == from_wei(FVal(rdn_balance))
        assert FVal(per_account[eth_acc2]['usd_value']) > ZERO

    if totals_only:
        totals = result
    else:
        totals = result['totals']
    if also_btc:
        assert len(totals) == 3
    else:
        assert len(totals) == 2

    assert FVal(totals['ETH']['amount']) == (
        from_wei(FVal(eth_balance1)) +
        from_wei(FVal(eth_balance2))
    )
    assert FVal(totals['ETH']['usd_value']) > ZERO
    assert FVal(totals['RDN']['amount']) == from_wei(FVal(rdn_balance))
    assert FVal(totals['RDN']['usd_value']) > ZERO


def mock_etherscan_balances_query(
        eth_map: Dict[str, str],
        btc_map: Dict[str, str],
        original_requests_get,
):

    def mock_requests_get(url, *args, **kwargs):
        if 'etherscan.io/api?module=account&action=balancemulti' in url:
            accounts = []
            for addr, value in eth_map.items():
                accounts.append({'account': addr, 'balance': value['ETH']})
            response = f'{{"status":"1","message":"OK","result":{json.dumps(accounts)}}}'
        elif 'api.etherscan.io/api?module=account&action=tokenbalance' in url:
            response = '{"status":"1","message":"OK","result":"0"}'
            for addr, value in eth_map.items():
                if addr in url and 'RDN' in value:
                    response = f'{{"status":"1","message":"OK","result":"{value["RDN"]}"}}'

        elif 'blockchain.info' in url:
            queried_addr = url.split('/')[-1]
            msg = f'Queried BTC address {queried_addr} is not in the given btc map to mock'
            assert queried_addr in btc_map, msg
            response = btc_map[queried_addr]

        else:
            return original_requests_get(url, *args, **kwargs)

        return MockResponse(200, response)

    return patch('rotkehlchen.utils.misc.requests.get', wraps=mock_requests_get)
