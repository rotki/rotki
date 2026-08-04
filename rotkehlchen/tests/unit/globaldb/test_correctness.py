from typing import TYPE_CHECKING

from eth_utils.address import to_checksum_address

from rotkehlchen.tests.conftest import TestEnvironment, requires_env
from rotkehlchen.tests.utils.globaldb import find_non_checksummed_addresses_in_db

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


def test_checksummed_values(globaldb: GlobalDBHandler):
    """Test that addresses and identifiers have checksummed addresses"""
    cursor = globaldb.conn.cursor()
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
    cursor.close()


@requires_env([TestEnvironment.NIGHTLY])  # sweeps the whole packaged db, and it rarely changes
def test_packaged_db_addresses_are_checksummed(globaldb: GlobalDBHandler):
    """Test that every evm address the packaged globaldb ships is checksummed.

    Asset identifiers are compared exactly, so an identifier built around a non canonical
    address matches nothing built around the canonical one, and the globaldb's NOCASE
    identifier hides that from every lookup that goes through it. Whatever we ship is the
    one part of a user's globaldb we can keep correct up front, so a wrongly cased address
    must never leave the repo. The rest can only be repaired by the v16->v17 upgrade.
    """
    with globaldb.conn.read_ctx() as cursor:
        bad_values = find_non_checksummed_addresses_in_db(cursor)

    assert bad_values == [], 'Found non checksummed evm addresses in the packaged globaldb:\n' + '\n'.join(bad_values)  # noqa: E501
