import io
import json
import logging
import os
import shutil
import subprocess
import sys
if os.name != 'nt':
     # termios does not exist in windows
    import termios

from binascii import hexlify

import gevent
from web3.middleware import geth_poa_middleware

from rotkehlchen.crypto import address_encoder, privatekey_to_address
from rotkehlchen.tests.utils.genesis import GENESIS_STUB

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


def geth_wait_and_check(ethchain_client, rpc_port, privatekeys, random_marker):
    """ Wait until the geth cluster is ready. """
    jsonrpc_running = False

    tries = 5
    while not jsonrpc_running and tries > 0:
        success, _ = ethchain_client.attempt_connect(rpc_port, mainnet_check=False)
        if not success:
            gevent.sleep(0.5)
            tries -= 1
        else:
            # inject the web3 middleware for PoA to not fail at extraData validation
            # https://github.com/ethereum/web3.py/issues/549
            ethchain_client.web3.middleware_stack.inject(geth_poa_middleware, layer=0)
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
    if os.name != 'nt' and isinstance(sys.stdin, io.IOBase):  # check that the test is running on non-capture mode
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
        geth_wait_and_check(ethchain_client, gethrpcport, private_keys, random_marker)
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
