from typing import Callable, Dict, List, Optional

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
    AddressNameSource,
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
                    ens_mappings[cached_value.address] = cached_value.name  # type: ignore
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
) -> Dict[ChecksumEvmAddress, Optional[str]]:
    """This method searches for all names of provided addresses known to rotki. We can show
    only one name per address, and thus we prioritize known names. Priority is read from settings.
    """

    prioritizer = NamePrioritizer(database)
    prioritizer.add_fetchers({
        'blockchain_account': blockchain_address_to_name,
        'global_addressbook': global_addressbook_address_to_name,
        'private_addressbook': private_addressbook_address_to_name,
        'ethereum_tokens': token_mappings_address_to_name,
        'hardcoded_mappings': hardcoded_address_to_name,
        'ens_names': ens_address_to_name,
    })

    with database.conn.read_ctx() as cursor:
        settings = database.get_settings(cursor)

    prioritized_addresses = prioritizer.get_prioritized_names(
        settings.address_name_priority,
        addresses,
    )

    return prioritized_addresses


FetcherFunc = Callable[[DBHandler, ChecksumEvmAddress], Optional[str]]


class NamePrioritizer:
    _fetchers: Dict[AddressNameSource, FetcherFunc] = {}
    _db: DBHandler

    def __init__(self, database: DBHandler):
        self._db = database

    def add_fetchers(self, fetchers: Dict[AddressNameSource, FetcherFunc]) -> None:
        self._fetchers.update(fetchers)

    def get_prioritized_names(
            self,
            prioritized_name_source: List[AddressNameSource],
            addresses: List[ChecksumEvmAddress],
    ) -> Dict[ChecksumEvmAddress, Optional[str]]:
        """
        Gets the name from the name source with the highest priority.
        Name source ids with lower index have a higher priority.
        """
        top_prio_names: Dict[ChecksumEvmAddress, Optional[str]] = {}

        for address in addresses:
            for name_source in prioritized_name_source:
                fetcher = self._fetchers.get(name_source)
                if not fetcher:
                    raise NotImplementedError(
                        f'address name fetcher for "{name_source}" is not implemented',
                    )

                name = fetcher(self._db, address)
                if not name:
                    continue
                top_prio_names[address] = name
                break

        return top_prio_names


def blockchain_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
) -> Optional[str]:
    """Returns the label of an ethereum blockchain account with the given address or
    None if there is no such account or the account has no label set.
    """
    with db.conn.read_ctx() as cursor:
        return db.get_blockchain_account_label(
            cursor,
            SupportedBlockchain.ETHEREUM,
            address,
        )


def private_addressbook_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
) -> Optional[str]:
    """Returns the name of a private addressbook entry with the given address or
    None if there is no such entry or the entry has no name set.
    """
    db_addressbook = DBAddressbook(db)
    return db_addressbook.get_addressbook_entry_name(
        AddressbookType.PRIVATE,
        address,
    )


def global_addressbook_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
) -> Optional[str]:
    """Returns the name of a global addressbook entry with the given address or
    None if there is no such entry or the entry has no name set.
    """
    db_addressbook = DBAddressbook(db)
    return db_addressbook.get_addressbook_entry_name(
        AddressbookType.GLOBAL,
        address,
    )


def hardcoded_address_to_name(
        _: DBHandler,
        address: ChecksumEvmAddress,
) -> Optional[str]:
    """Returns the name of a known address or None if there is no such address"""
    return ETHADDRESS_TO_KNOWN_NAME.get(address, None)


def token_mappings_address_to_name(
        _: DBHandler,
        address: ChecksumEvmAddress,
) -> Optional[str]:
    """Returns the token name for a token address in the global database or None
    if the address is no token address
    """
    token_mappings = GlobalDBHandler().get_tokens_mappings(addresses=[address])
    return token_mappings.get(address, None)


def ens_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
) -> Optional[str]:
    """Returns the ens name for an address or None if the address doesn't have one"""
    db_ens = DBEns(db)

    with db.conn.read_ctx() as cursor:
        db_reverse_ens = db_ens.get_reverse_ens(cursor, addresses=[address])
        address_ens = db_reverse_ens.get(address, None)
        if isinstance(address_ens, EnsMapping):
            return address_ens.name

        return None
