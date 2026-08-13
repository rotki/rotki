import json
from typing import TYPE_CHECKING, Any

import pytest
from eth_utils import is_checksum_address

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract, checksum_decoded_addresses
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


def test_evm_contracts_data(globaldb: Any) -> None:
    """Test that all evm contract entries in the packaged global DB have legal data"""
    serialized_chain_ids = [x.serialize_for_db() for x in ChainID]
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute('SELECT address, chain_id, abi, deployed_block FROM contract_data')
        for entry in cursor:
            assert is_checksum_address(entry[0])
            assert isinstance(entry[1], int) and entry[1] in serialized_chain_ids
            assert isinstance(entry[2], int)
            assert isinstance(entry[3], int) and entry[3] >= 0


def test_evm_abi_data(globaldb: Any) -> None:
    """Test that the evm abi entries in the packaged globalDB have legal data"""
    abis_set: set[int | str] = {0}
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


@pytest.mark.parametrize('sql_vm_instructions_cb', [2])
def test_fallback_to_packaged_db(ethereum_inquirer: EthereumInquirer) -> None:
    """
    Test that if a contract / abi is missing in the globaldb, it is searched in the packaged db.
    """
    with GlobalDBHandler().conn.write_ctx() as cursor:
        # Delete one contract and its abi
        cursor.execute(
            'SELECT contract_data.address, contract_abi.value FROM contract_data INNER JOIN '
            'contract_abi ON contract_data.abi=contract_abi.id WHERE chain_id=1 LIMIT 1',
        )
        (address, abi) = cursor.fetchone()  # There has to be at least one entry
        cursor.execute('DELETE FROM contract_data WHERE address=? AND chain_id=1', (address,))
        cursor.execute('DELETE FROM contract_abi WHERE value=?', (abi,))

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


def test_checksum_decoded_addresses() -> None:
    """Test that address outputs get checksummed at any array/tuple nesting depth.

    Gnosis Pay's admins helper returns address[][] and gitcoin's getRecipient returns a
    struct holding an address, so both containers need to be walked.
    """
    assert checksum_decoded_addresses(
        values=(
            '0x37f18a82493cdf80675ff01e58c1a1b39637cf50',
            ['0xc37b40abdb939635068d3c5f13e7faf686f03b65'],
            ((), ('0x37f18a82493cdf80675ff01e58c1a1b39637cf50',)),
            (False, '0x37f18a82493cdf80675ff01e58c1a1b39637cf50', (1, 'ipfs://example')),
            (('0xc37b40abdb939635068d3c5f13e7faf686f03b65', 5),),
            42,
        ),
        output_types=[
            'address',
            'address[]',
            'address[][]',
            '(bool,address,(uint256,string))',
            '(address,uint256)[]',
            'uint256',
        ],
    ) == (
        '0x37f18A82493cdF80675fF01e58c1A1b39637cf50',
        ['0xc37b40ABdB939635068d3c5f13E7faF686F03B65'],
        ((), ('0x37f18A82493cdF80675fF01e58c1A1b39637cf50',)),
        (False, '0x37f18A82493cdF80675fF01e58c1A1b39637cf50', (1, 'ipfs://example')),
        (('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 5),),
        42,
    )


def test_decode_of_unexpected_output_raises_deserialization_error() -> None:
    """An answer that does not match the abi must surface as a DeserializationError.

    A call that a node reports as successful can still come back with data that does not
    decode, a contract hitting its fallback function being the common case, and every caller
    of decode() is written to handle a DeserializationError.
    """
    with pytest.raises(DeserializationError):
        EvmContract(
            address=ZERO_ADDRESS,
            abi=[{'inputs': [], 'name': 'token', 'outputs': [{'name': '', 'type': 'address'}], 'stateMutability': 'view', 'type': 'function'}],  # noqa: E501
        ).decode(result=b'', method_name='token')
