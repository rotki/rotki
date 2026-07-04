import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Final, NamedTuple, cast

from rotkehlchen.chain.ethereum.decoding.constants import (
    KRAKEN_ADDRESSES,
    POLONIEX_ADDRESS,
    UPHOLD_ADDRESS,
)
from rotkehlchen.chain.ethereum.modules.gwei_names.naming import gns_resolve, gns_reverse_lookup
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


class NamingSystem(NamedTuple):
    """An on-chain naming system resolving names to addresses and back.

    The identifier is stored in the source column of the ens_mappings cache table,
    while source is the entry of the address_name_priority setting controlling it.
    An empty suffix means the system is the default one for forward resolution.
    """
    identifier: str
    source: AddressNameSource
    suffix: str
    reverse_lookup: Callable[['EthereumInquirer', list[ChecksumEvmAddress]], dict[ChecksumEvmAddress, str | None]]  # noqa: E501
    resolve: Callable[['EthereumInquirer', str], ChecksumEvmAddress | None]


def _ens_reverse_lookup(
        inquirer: 'EthereumInquirer',
        addresses: list[ChecksumEvmAddress],
) -> dict[ChecksumEvmAddress, str | None]:
    return inquirer.ens_reverse_lookup(addresses)


def _ens_resolve(inquirer: 'EthereumInquirer', name: str) -> ChecksumEvmAddress | None:
    return inquirer.ens_lookup(name)


ENS_NAMING_SYSTEM: Final = NamingSystem(
    identifier='ens',
    source='ens_names',
    suffix='',  # ENS is the default system, handling .eth and DNS names
    reverse_lookup=_ens_reverse_lookup,
    resolve=_ens_resolve,
)
GNS_NAMING_SYSTEM: Final = NamingSystem(
    identifier='gns',
    source='gns_names',
    suffix='.gwei',
    reverse_lookup=gns_reverse_lookup,
    resolve=gns_resolve,
)
ETHEREUM_NAMING_SYSTEMS: Final = (ENS_NAMING_SYSTEM, GNS_NAMING_SYSTEM)


def _find_system_name_mappings(
        dbens: DBEns,
        ethereum_inquirer: 'EthereumInquirer',
        system: NamingSystem,
        addresses: list[ChecksumEvmAddress],
        ignore_cache: bool,
) -> dict[ChecksumEvmAddress, str]:
    """
    Find and return the given naming system's names for the given addresses.
    First check the db, and if can't find, call the blockchain.

    May raise:
    - RemoteError if was not able to query blockchain
    """
    name_mappings: dict[ChecksumEvmAddress, str] = {}
    if ignore_cache:
        addresses_to_query = addresses
    else:
        addresses_to_query = []
        with dbens.db.conn.read_ctx() as cursor:
            cached_data = dbens.get_reverse_ens(
                cursor=cursor,
                addresses=addresses,
                source=system.identifier,
            )
        cur_time = ts_now()
        for address, cached_value in cached_data.items():
            has_name = isinstance(cached_value, EnsMapping)
            last_update: Timestamp = cached_value.last_update if has_name else cached_value  # type: ignore  # mypy doesn't see `isinstance` check
            if cur_time - last_update > ENS_UPDATE_INTERVAL:
                addresses_to_query.append(address)
            elif has_name:
                name_mappings[cached_value.address] = cached_value.name  # type: ignore
        addresses_to_query += list(set(addresses) - set(cached_data.keys()))

    try:
        query_results = system.reverse_lookup(ethereum_inquirer, addresses_to_query)
    except (RemoteError, BlockchainQueryError) as e:
        raise RemoteError(f'Error occurred while querying {system.identifier} names: {e!s}') from e

    with dbens.db.user_write() as write_cursor:
        return dbens.update_values(
            write_cursor=write_cursor,
            ens_lookup_results=query_results,
            mappings_to_send=name_mappings,
            source=system.identifier,
        )


def find_ens_mappings(
        ethereum_inquirer: 'EthereumInquirer',
        addresses: list[ChecksumEvmAddress],
        ignore_cache: bool,
) -> dict[ChecksumEvmAddress, str]:
    """
    Find and return names for the given addresses from all enabled naming systems.
    First check the db, and if can't find, call the blockchain.

    ENS is always queried, keeping the old behavior of this endpoint. Other naming
    systems are only queried if their source is in the address_name_priority setting,
    since their lookups cost extra on-chain queries. When an address has a name in
    several systems the one from the system with the highest priority is returned.

    IMPORTANT: If this implementation changes also change the one in tests/api/test_ens.py

    May raise:
    - RemoteError if was not able to query blockchain
    """
    dbens = DBEns(ethereum_inquirer.database)
    priority: Sequence[AddressNameSource] = CachedSettings().get_entry('address_name_priority')  # type: ignore  # mypy doesn't detect correctly the type of the cached setting
    enabled_systems = [
        system for system in ETHEREUM_NAMING_SYSTEMS
        if system.identifier == ENS_NAMING_SYSTEM.identifier or system.source in priority
    ]
    enabled_systems.sort(  # sort from lowest to highest priority so higher priority names win the merge below. Systems queried without being in the priority list get the lowest priority.  # noqa: E501
        key=lambda system: priority.index(system.source) if system.source in priority else len(priority),  # noqa: E501
        reverse=True,
    )
    mappings: dict[ChecksumEvmAddress, str] = {}
    for system in enabled_systems:
        mappings.update(_find_system_name_mappings(
            dbens=dbens,
            ethereum_inquirer=ethereum_inquirer,
            system=system,
            addresses=addresses,
            ignore_cache=ignore_cache,
        ))

    return mappings


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
    """Resolve name by either checking the DB or asking the chain.

    The naming system is picked by the name's suffix (e.g. .gwei names resolve
    via GNS), defaulting to ENS.
    """
    dbens = DBEns(ethereum_inquirer.database)
    if not ignore_cache:
        with dbens.db.conn.read_ctx() as cursor:
            if (resolved_name := dbens.get_address_for_name(
                cursor=cursor,
                name=name,
            )) is not None:
                return resolved_name

    system = next(
        (x for x in ETHEREUM_NAMING_SYSTEMS if x.suffix != '' and name.endswith(x.suffix)),
        ENS_NAMING_SYSTEM,
    )
    try:
        resolved_address = system.resolve(ethereum_inquirer, name)
    except (RemoteError, InputError) as e:
        log.debug('Could not resolve %s name %s to an address due to %s', system.identifier, name, e)  # noqa: E501
        resolved_address = None

    if resolved_address is None:
        return None

    with dbens.db.user_write() as write_cursor:
        dbens.update_values(  # update cache if needed
            write_cursor=write_cursor,
            ens_lookup_results={resolved_address: name},
            mappings_to_send={},
            source=system.identifier,
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
            'gns_names': _gns_address_to_name,
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


def _naming_system_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
        source: str,
) -> str | None:
    """Returns the name of the given naming system for an address or
    None if the address doesn't have one
    """
    db_ens = DBEns(db)
    with db.conn.read_ctx() as cursor:
        db_reverse_ens = db_ens.get_reverse_ens(
            cursor=cursor,
            addresses=[chain_address.address],
            source=source,
        )
        address_ens = db_reverse_ens.get(chain_address.address, None)
        if isinstance(address_ens, EnsMapping):
            return address_ens.name

        return None


def _ens_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the ens name for an address or None if the address doesn't have one"""
    return _naming_system_address_to_name(
        db=db,
        chain_address=chain_address,
        source=ENS_NAMING_SYSTEM.identifier,
    )


def _gns_address_to_name(
        db: DBHandler,
        chain_address: OptionalChainAddress,
) -> str | None:
    """Returns the gwei name for an address or None if the address doesn't have one"""
    return _naming_system_address_to_name(
        db=db,
        chain_address=chain_address,
        source=GNS_NAMING_SYSTEM.identifier,
    )
