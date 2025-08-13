import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, cast

from rotkehlchen.chain.ethereum.decoding.constants import (
    KRAKEN_ADDRESSES,
    POLONIEX_ADDRESS,
    UPHOLD_ADDRESS,
)
from rotkehlchen.constants import ENS_UPDATE_INTERVAL
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ens import DBEns
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import BlockchainQueryError, InputError, RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    AddressbookEntryWithSource,
    AddressbookType,
    AddressNameSource,
    ChainAddress,
    ChecksumEvmAddress,
    EnsMapping,
    OptionalChainAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def find_ens_mappings(
        ethereum_inquirer: 'EthereumInquirer',
        addresses: list[ChecksumEvmAddress],
        ignore_cache: bool,
) -> dict[ChecksumEvmAddress, str]:
    """
    Find and return ens names for the given addresses.
    First check the db, and if can't find, call the blockchain.

    IMPORTANT: If this implementation changes also change the one in tests/api/test_ens.py

    May raise:
    - RemoteError if was not able to query blockchain
    """
    dbens = DBEns(ethereum_inquirer.database)
    ens_mappings: dict[ChecksumEvmAddress, str] = {}
    if ignore_cache:
        addresses_to_query = addresses
    else:
        addresses_to_query = []
        with dbens.db.conn.read_ctx() as cursor:
            cached_data = dbens.get_reverse_ens(cursor=cursor, addresses=addresses)
        cur_time = ts_now()
        for address, cached_value in cached_data.items():
            has_name = isinstance(cached_value, EnsMapping)
            last_update: Timestamp = cached_value.last_update if has_name else cached_value  # type: ignore  # mypy doesn't see `isinstance` check
            if cur_time - last_update > ENS_UPDATE_INTERVAL:
                addresses_to_query.append(address)
            elif has_name:
                ens_mappings[cached_value.address] = cached_value.name  # type: ignore
        addresses_to_query += list(set(addresses) - set(cached_data.keys()))

    try:
        query_results = ethereum_inquirer.ens_reverse_lookup(addresses_to_query)
    except (RemoteError, BlockchainQueryError) as e:
        raise RemoteError(f'Error occurred while querying ens names: {e!s}') from e

    with dbens.db.user_write() as write_cursor:
        return dbens.update_values(
            write_cursor=write_cursor,
            ens_lookup_results=query_results,
            mappings_to_send=ens_mappings,
        )


def search_for_addresses_names(
        prioritizer: 'NamePrioritizer',
        chain_addresses: list[OptionalChainAddress],
) -> list[AddressbookEntryWithSource]:
    """
    This method searches for all names of provided addresses known to rotki. We can show
    only one name per address, and thus we prioritize known names. Priority is read from settings.

    For now this works only for evm chains.
    TODO: support not only ChecksumEvmAddress, but other address formats too.
    """
    return prioritizer.get_prioritized_names(
        prioritized_name_source=CachedSettings().get_entry('address_name_priority'),  # type: ignore  # mypy doesn't detect correctly the type of the cached setting
        chain_addresses=chain_addresses,
    )


def maybe_resolve_name(
        ethereum_inquirer: 'EthereumInquirer',
        name: str,
        ignore_cache: bool,
) -> ChecksumEvmAddress | None:
    """Resolve name by either checking the DB or asking the chain"""
    dbens = DBEns(ethereum_inquirer.database)
    if not ignore_cache:
        with dbens.db.conn.read_ctx() as cursor:
            if (resolved_name := dbens.get_address_for_name(
                cursor=cursor,
                name=name,
            )) is not None:
                return resolved_name

    try:
        resolved_address = ethereum_inquirer.ens_lookup(name)
    except (RemoteError, InputError) as e:
        log.debug(f'Could not resolve ENS {name} to an address due to {e}')
        resolved_address = None

    if resolved_address is None:
        return None

    with dbens.db.user_write() as write_cursor:
        dbens.update_values(  # update cache if needed
            write_cursor=write_cursor,
            ens_lookup_results={resolved_address: name},
            mappings_to_send={},
        )
    return resolved_address


FetcherFunc = Callable[[DBHandler, OptionalChainAddress], str | None]


class NamePrioritizer:
    def __init__(self, database: DBHandler):
        self._fetchers: dict[AddressNameSource, FetcherFunc] = {}
        self._db = database
        self.add_fetchers({
            'blockchain_account': _blockchain_address_to_name,
            'global_addressbook': _global_addressbook_address_to_name,
            'private_addressbook': _private_addressbook_address_to_name,
            'ethereum_tokens': _token_mappings_address_to_name,
            'hardcoded_mappings': _hardcoded_address_to_name,
            'ens_names': _ens_address_to_name,
        })

    def add_fetchers(self, fetchers: dict[AddressNameSource, FetcherFunc]) -> None:
        self._fetchers.update(fetchers)

    def get_prioritized_names(
            self,
            prioritized_name_source: Sequence[AddressNameSource],
            chain_addresses: list[OptionalChainAddress],
    ) -> list[AddressbookEntryWithSource]:
        """
        Gets the name from the name source with the highest priority.
        Name source ids with lower index have a higher priority.
        """
        top_prio_names = []

        for chain_address in chain_addresses:
            for name_source in prioritized_name_source:
                fetcher = self._fetchers.get(name_source)
                if not fetcher:
                    raise NotImplementedError(
                        f'address name fetcher for "{name_source}" is not implemented',
                    )

                name: str | None = fetcher(self._db, chain_address)
                if name is None:
                    continue
                top_prio_names.append(AddressbookEntryWithSource(
                    name=name,
                    address=chain_address.address,
                    blockchain=chain_address.blockchain,
                    source=name_source,
                ))
                break

        return top_prio_names


def _blockchain_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the label of an evm blockchain account with the given address or
    None if there is no such account or the account has no label set or blockchain is
    not specified.
    """
    if chain_address.blockchain is None:
        return None

    chain_address = cast('ChainAddress', chain_address)
    return DBAddressbook(db).get_addressbook_entry_name(AddressbookType.PRIVATE, chain_address)


def _private_addressbook_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the name of a private addressbook entry with the given address or
    None if there is no such entry or the entry has no name set.
    """
    db_addressbook = DBAddressbook(db)
    return db_addressbook.get_addressbook_entry_name(
        book_type=AddressbookType.PRIVATE,
        chain_address=chain_address,
    )


def _global_addressbook_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the name of a global addressbook entry with the given address or
    None if there is no such entry or the entry has no name set.
    """
    db_addressbook = DBAddressbook(db)
    return db_addressbook.get_addressbook_entry_name(
        book_type=AddressbookType.GLOBAL,
        chain_address=chain_address,
    )


def _hardcoded_address_to_name(
        _: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the name of a known address or None if there is no such address"""
    if chain_address.blockchain != SupportedBlockchain.ETHEREUM:
        return None

    if chain_address.address in KRAKEN_ADDRESSES:
        return 'Kraken'
    elif chain_address.address == POLONIEX_ADDRESS:
        return 'Poloniex'
    elif chain_address.address == UPHOLD_ADDRESS:
        return 'Uphold.com'

    return None


def _token_mappings_address_to_name(
        _: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the token name for a token address/chain id combination
    in the global database or None if the address is no token address
    """
    if chain_address.blockchain is None or not chain_address.blockchain.is_evm():
        return None
    return GlobalDBHandler.get_token_name(address=chain_address.address, chain_id=chain_address.blockchain.to_chain_id())  # noqa: E501


def _ens_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the ens name for an address or None if the address doesn't have one"""
    db_ens = DBEns(db)
    with db.conn.read_ctx() as cursor:
        db_reverse_ens = db_ens.get_reverse_ens(
            cursor=cursor,
            addresses=[chain_address.address],
        )
        address_ens = db_reverse_ens.get(chain_address.address, None)
        if isinstance(address_ens, EnsMapping):
            return address_ens.name

        return None
