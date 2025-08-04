from eth_utils.address import to_checksum_address

from rotkehlchen.globaldb.handler import GlobalDBHandler


def test_checksummed_values(globaldb: GlobalDBHandler):
    """Test that addresses and identifiers have checksummed addresses"""
    with globaldb.conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT evm_tokens.identifier, address, name, symbol FROM evm_tokens JOIN '
            'common_asset_details ON evm_tokens.identifier=common_asset_details.identifier '
            'JOIN assets ON evm_tokens.identifier=assets.identifier',
        )
        identifiers = set()
        for identifier, address, name, symbol in cursor:
            checksummed_address = to_checksum_address(address)
            assert checksummed_address == address
            assert checksummed_address in identifier
            assert name != identifier
            assert symbol != identifier
            identifiers.add(identifier)

        cursor.execute('SELECT asset FROM multiasset_mappings')
        assert {x[0] for x in cursor if x[0].startswith('eip155')}.issubset(identifiers)
