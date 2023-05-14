import json

import gevent
from eth_utils import is_checksum_address

from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import ChainID


def test_evm_contracts_data(globaldb):
    """Test that all evm contract entries in the packaged global DB have legal data"""
    serialized_chain_ids = [x.serialize_for_db() for x in ChainID]
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('SELECT address, chain_id, abi, deployed_block FROM contract_data')
        for entry in cursor:
            assert is_checksum_address(entry[0])
            assert isinstance(entry[1], int) and entry[1] in serialized_chain_ids
            assert isinstance(entry[2], int)
            assert isinstance(entry[3], int) and entry[3] > 0


def test_evm_abi_data(globaldb):
    """Test that the evm abi entries in the packaged globalDB have legal data"""
    abis_set = {0}
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('SELECT id, value FROM contract_abi')
        for entry in cursor:
            assert isinstance(entry[0], int)
            # read the abi, and make sure it's the most compressed version it can be
            # and that it's unique
            assert isinstance(entry[1], str)
            json_abi = json.loads(entry[1])
            serialized_abi = json.dumps(json_abi, separators=(',', ':'))
            assert serialized_abi == entry[1]
            assert entry[1] not in abis_set
            abis_set.add(entry[1])


def keep_open_globaldb_write(builtin_db_path):
    """Silly way to keep a transaction open in another greenlet"""
    with GlobalDBHandler().packaged_db_lock, GlobalDBHandler().conn.write_ctx() as cursor:
        cursor.execute(f'ATTACH DATABASE "{builtin_db_path}" AS packaged_db;')
        gevent.sleep(1.5)
        cursor.execute('DETACH DATABASE "packaged_db"')


def test_fallback_to_packaged_db(ethereum_inquirer: 'EthereumInquirer'):
    """
    Test that if a contract / abi is missing in the globaldb, it is searched in the packaged db.
    """
    with GlobalDBHandler().conn.read_ctx() as cursor:
        # Delete one contract and its abi
        cursor.execute(
            'SELECT contract_data.address, contract_abi.value FROM contract_data INNER JOIN '
            'contract_abi ON contract_data.abi=contract_abi.id WHERE chain_id=1 LIMIT 1',
        )
        (address, abi) = cursor.fetchone()  # There has to be at least one entry
        cursor.execute('DELETE FROM contract_data WHERE address=? AND chain_id=1', (address,))
        cursor.execute('DELETE FROM contract_abi WHERE value=?', (abi,))

    # open and keep open a write context, to make sure we are in a transaction
    # long enough to last when we do attach/detach in contracts.contract()
    gevent.spawn(keep_open_globaldb_write, ethereum_inquirer.contracts.builtin_database_path)
    gevent.sleep(.3)  # context switch for a bit to let the other greenlet run
    # Now query the contract, let it get to packaged global DB and also see that
    # database packaged_db is locked is also not raised
    ethereum_inquirer.contracts.contract(address)

    with GlobalDBHandler().conn.read_ctx() as cursor:
        # Check that the contract and the abi were copied to the global db
        cursor.execute(
            'SELECT COUNT(*) FROM contract_data INNER JOIN '
            'contract_abi ON contract_data.abi=contract_abi.id WHERE chain_id=1 AND '
            'contract_data.address=? AND contract_abi.value=?',
            (address, abi),
        )
        assert cursor.fetchone()[0] == 1
