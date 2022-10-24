from abc import ABC, abstractmethod
from typing import Dict, List

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

    prioritizer = NamePrioritizer()
    prioritizer.add_fetchers({
        'blockchain_account': BlockchainAccountLabelFetcher(database),
        'global_addressbook': GlobalAddressBookFetcher(database),
        'private_addressbook': PrivateAddressBookFetcher(database),
        'ethereum_tokens': TokenMappingsFetcher(database),
        'hardcoded_mappings': HardcodedAddressFetcher(database),
        'ens_names': ENSFetcher(database),
    })

    prioritized_addresses = prioritizer.get_prioritized_names(DEFAULT_ADDRESS_NAME_PRIORITY, addresses)

    return prioritized_addresses


class NameFetcher(ABC):
    """
    Each source, where a name of an address might be stored, is represented by an implementation of this
    abstract class.
    """
    _db: DBHandler

    def __init__(self, db: DBHandler):
        self._db = db

    @abstractmethod
    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        pass


class NamePrioritizer:
    _fetchers: Dict[str, NameFetcher] = {}

    def add_fetchers(self, fetchers: Dict[AddressNameSource, NameFetcher]):
        self._fetchers.update(fetchers)

    def get_prioritized_names(self, prioritized_name_source: List[AddressNameSource],
                              addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        """
        Gets the name from the name source with the highest priority.
        Name source ids with lower index have a higher priority.
        """
        top_prio_names: Dict[ChecksumEvmAddress, str] = {}

        for name_source in prioritized_name_source:
            fetcher = self._fetchers.get(name_source)
            if not fetcher:
                raise NotImplementedError(f"address name fetcher for '{name_source}' is not implemented")

            addresses_names = fetcher.get_addresses_names(addresses)
            for address_name in addresses_names.items():
                address, name = address_name

                # Has already found a name with higher prio?
                if top_prio_names.get(address) is not None:
                    continue

                if name:
                    top_prio_names[address] = name

        return top_prio_names


class BlockchainAccountLabelFetcher(NameFetcher):
    _labels: Dict[BlockchainAddress, str]

    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        result_mappings: Dict[ChecksumEvmAddress, str] = {}
        addresses_set = set(addresses)
        with self._db.conn.read_ctx() as cursor:
            accounts_data = self._db.get_blockchain_account_data(
                cursor=cursor,
                blockchain=SupportedBlockchain.ETHEREUM,
            )

        for account in accounts_data:
            if account.address in addresses_set and account.label:
                result_mappings[account.address] = account.label

        return result_mappings


def result_from_addressbook_entries(addressbook_entries: List[AddressbookEntry]) \
        -> Dict[ChecksumEvmAddress, str]:
    result_mappings: Dict[ChecksumEvmAddress, str] = {}
    for addressbook_entry in addressbook_entries:
        result_mappings[addressbook_entry.address] = addressbook_entry.name

    return result_mappings


class PrivateAddressBookFetcher(NameFetcher):
    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        db_addressbook = DBAddressbook(self._db)
        with self._db.conn.read_ctx() as cursor:
            addressbook_entries = db_addressbook.get_addressbook_entries(
                cursor=cursor,
                addresses=addresses,
            )
        return result_from_addressbook_entries(addressbook_entries)


class GlobalAddressBookFetcher(NameFetcher):

    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        db_addressbook = DBAddressbook(self._db)
        with db_addressbook.read_ctx(AddressbookType.GLOBAL) as global_cursor:
            addressbook_entries = db_addressbook.get_addressbook_entries(
                cursor=global_cursor,
                addresses=addresses,
            )
        return result_from_addressbook_entries(addressbook_entries)


class HardcodedAddressFetcher(NameFetcher):
    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        result_mappings: Dict[ChecksumEvmAddress, str] = {}

        for address in addresses:
            constant_name = ETHADDRESS_TO_KNOWN_NAME.get(address)
            if constant_name is not None:
                result_mappings[address] = constant_name

        return result_mappings


class TokenMappingsFetcher(NameFetcher):
    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        result_mappings: Dict[ChecksumEvmAddress, str] = {}
        token_mappings = GlobalDBHandler().get_tokens_mappings(addresses=addresses)

        for token_address, name in token_mappings.items():
            if name:
                result_mappings[token_address] = name
        return result_mappings


class ENSFetcher(NameFetcher):

    def get_addresses_names(self, addresses: List[ChecksumEvmAddress]) -> Dict[ChecksumEvmAddress, str]:
        result_mappings: Dict[ChecksumEvmAddress, str] = {}
        db_ens = DBEns(self._db)

        with self._db.conn.read_ctx() as cursor:
            db_reverse_ens = db_ens.get_reverse_ens(cursor, addresses=addresses)
            reverse_ens = list(db_reverse_ens.values())

        for mapping in reverse_ens:
            if isinstance(mapping, EnsMapping):
                if mapping.name:
                    result_mappings[mapping.address] = mapping.name
        return result_mappings
