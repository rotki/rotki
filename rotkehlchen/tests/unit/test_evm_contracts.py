import json

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
