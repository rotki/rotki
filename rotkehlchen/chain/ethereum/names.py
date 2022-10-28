from typing import Dict, List

from eth_utils import to_checksum_address

from rotkehlchen.chain.ethereum.decoding.constants import ETHADDRESS_TO_KNOWN_NAME
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.constants import ENS_UPDATE_INTERVAL
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ens import DBEns
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.types import (
    AddressbookType,
    ChecksumEvmAddress,
    EnsMapping,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now


def find_ens_mappings(
        ethereum_manager: EthereumManager,
        addresses: List[ChecksumEvmAddress],
        ignore_cache: bool,
) -> Dict[ChecksumEvmAddress, str]:
    """
    Find and return ens names for the given addresses.
    First check the db, and if can't find, call the blockchain.
    May raise:
    - RemoteError if was not able to query blockchain
    """
    dbens = DBEns(ethereum_manager.database)
    ens_mappings: Dict[ChecksumEvmAddress, str] = {}
    with dbens.db.user_write() as cursor:
        if ignore_cache:
            addresses_to_query = addresses
        else:
            addresses_to_query = []
            cached_data = dbens.get_reverse_ens(cursor, addresses)
            cur_time = ts_now()
            for address, cached_value in cached_data.items():
                has_name = isinstance(cached_value, EnsMapping)
                last_update: Timestamp = cached_value.last_update if has_name else cached_value  # type: ignore  # mypy doesn't see `isinstance` check  # noqa: E501
                if cur_time - last_update > ENS_UPDATE_INTERVAL:
                    addresses_to_query.append(address)
                elif has_name:
                    ens_mappings[cached_value.address] = cached_value.name  # type: ignore  # mypy doesn't see `isinstance` check  # noqa: E501
            addresses_to_query += list(set(addresses) - set(cached_data.keys()))

        try:
            query_results = ethereum_manager.ens_reverse_lookup(addresses_to_query)
        except (RemoteError, BlockchainQueryError) as e:
            raise RemoteError(f'Error occurred while querying ens names: {str(e)}') from e

        ens_mappings = dbens.update_values(
            write_cursor=cursor,
            ens_lookup_results=query_results,
            mappings_to_send=ens_mappings,
        )
    return ens_mappings


def search_for_addresses_names(
        database: DBHandler,
        addresses: List[ChecksumEvmAddress],
) -> Dict[ChecksumEvmAddress, str]:
    """This method searches for all names of provided addresses known to rotki. We can show
    only one name per address, and thus we prioritize known names. Priority is the following:
    blockchain account labels -> private addressbook -> global addressbook
    -> ethereum tokens -> hardcoded mappings -> ENS names.
    """
    db_addressbook = DBAddressbook(database)
    db_ens = DBEns(database)

    with database.conn.read_ctx() as cursor:
        reverse_ens = db_ens.get_reverse_ens(cursor, addresses=addresses).values()
        mapped_tokens = GlobalDBHandler().get_tokens_mappings(addresses=addresses)
        hardcoded_mappings = {}
        for address in addresses:
            constant_name = ETHADDRESS_TO_KNOWN_NAME.get(address)
            if constant_name is not None:
                hardcoded_mappings[address] = constant_name

        with db_addressbook.read_ctx(AddressbookType.GLOBAL) as global_cursor:
            global_addressbook = db_addressbook.get_addressbook_entries(
                cursor=global_cursor,
                addresses=addresses,
            )
        private_addressbook = db_addressbook.get_addressbook_entries(
            cursor=cursor,
            addresses=addresses,
        )
        addresses_set = set(addresses)
        labels = {}
        accounts_data = database.get_blockchain_account_data(
            cursor=cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
        )

    for account in accounts_data:
        if account.address in addresses_set:
            labels[account.address] = account.label

    result_mappings: Dict[ChecksumEvmAddress, str] = {}
    for mapping in reverse_ens:
        if isinstance(mapping, EnsMapping):
            result_mappings[mapping.address] = mapping.name
    for address, name in mapped_tokens.items():
        result_mappings[address] = name
    for hardcoded_address, hardcoded_name in hardcoded_mappings.items():
        result_mappings[hardcoded_address] = hardcoded_name
    for addressbook_entry in global_addressbook:
        result_mappings[addressbook_entry.address] = addressbook_entry.name
    for addr, label in labels.items():
        if label is not None:
            result_mappings[to_checksum_address(addr)] = label
    for addressbook_entry in private_addressbook:
        result_mappings[addressbook_entry.address] = addressbook_entry.name

    return result_mappings
