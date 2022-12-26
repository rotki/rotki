from typing import TYPE_CHECKING, Callable, Optional

from rotkehlchen.chain.ethereum.decoding.constants import ETHADDRESS_TO_KNOWN_NAME
from rotkehlchen.constants import ENS_UPDATE_INTERVAL
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ens import DBEns
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import (
    AddressbookType,
    AddressNameSource,
    ChecksumEvmAddress,
    EnsMapping,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


def find_ens_mappings(
        ethereum_inquirer: 'EthereumInquirer',
        addresses: list[ChecksumEvmAddress],
        ignore_cache: bool,
) -> dict[ChecksumEvmAddress, str]:
    """
    Find and return ens names for the given addresses.
    First check the db, and if can't find, call the blockchain.
    May raise:
    - RemoteError if was not able to query blockchain
    """
    dbens = DBEns(ethereum_inquirer.database)
    ens_mappings: dict[ChecksumEvmAddress, str] = {}
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
            query_results = ethereum_inquirer.ens_reverse_lookup(addresses_to_query)
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
        addresses: list[tuple[ChecksumEvmAddress, Optional[SupportedBlockchain]]],
) -> list[tuple[ChecksumEvmAddress, SupportedBlockchain, Optional[str]]]:
    """
    This method searches for all names of provided addresses known to rotki. We can show
    only one name per address, and thus we prioritize known names. Priority is read from settings.

    For now works only for evm chains.
    TODO: support not only ChecksumEvmAddress, but other address formats too.
    """
    prepared_addresses = []
    for address, blockchain in addresses:
        if blockchain is None:
            blockchain = SupportedBlockchain.ETHEREUM
        prepared_addresses.append((address, blockchain))

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
        prepared_addresses,
    )

    return prioritized_addresses


FetcherFunc = Callable[[DBHandler, ChecksumEvmAddress, SupportedBlockchain], Optional[str]]


class NamePrioritizer:
    def __init__(self, database: DBHandler):
        self._fetchers: dict[AddressNameSource, FetcherFunc] = {}
        self._db = database

    def add_fetchers(self, fetchers: dict[AddressNameSource, FetcherFunc]) -> None:
        self._fetchers.update(fetchers)

    def get_prioritized_names(
            self,
            prioritized_name_source: list[AddressNameSource],
            addresses: list[tuple[ChecksumEvmAddress, SupportedBlockchain]],
    ) -> list[tuple[ChecksumEvmAddress, SupportedBlockchain, Optional[str]]]:
        """
        Gets the name from the name source with the highest priority.
        Name source ids with lower index have a higher priority.
        """
        top_prio_names: list[tuple[ChecksumEvmAddress, SupportedBlockchain, Optional[str]]] = []

        for address, blockchain in addresses:
            for name_source in prioritized_name_source:
                fetcher = self._fetchers.get(name_source)
                if not fetcher:
                    raise NotImplementedError(
                        f'address name fetcher for "{name_source}" is not implemented',
                    )

                name = fetcher(self._db, address, blockchain)
                if not name:
                    continue
                top_prio_names.append((address, blockchain, name))
                break

        return top_prio_names


def blockchain_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
        blockchain: SupportedBlockchain,
) -> Optional[str]:
    """Returns the label of an ethereum blockchain account with the given address or
    None if there is no such account or the account has no label set.
    """
    with db.conn.read_ctx() as cursor:
        return db.get_blockchain_account_label(
            cursor=cursor,
            blockchain=blockchain,
            address=address,
        )


def private_addressbook_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
        blockchain: SupportedBlockchain,
) -> Optional[str]:
    """Returns the name of a private addressbook entry with the given address or
    None if there is no such entry or the entry has no name set.
    """
    db_addressbook = DBAddressbook(db)
    return db_addressbook.get_addressbook_entry_name(
        book_type=AddressbookType.PRIVATE,
        address=address,
        blockchain=blockchain,
    )


def global_addressbook_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
        blockchain: SupportedBlockchain,
) -> Optional[str]:
    """Returns the name of a global addressbook entry with the given address or
    None if there is no such entry or the entry has no name set.
    """
    db_addressbook = DBAddressbook(db)
    return db_addressbook.get_addressbook_entry_name(
        book_type=AddressbookType.GLOBAL,
        address=address,
        blockchain=blockchain,
    )


def hardcoded_address_to_name(
        _: DBHandler,
        address: ChecksumEvmAddress,
        blockchain: SupportedBlockchain,
) -> Optional[str]:
    """Returns the name of a known address or None if there is no such address"""
    if blockchain != SupportedBlockchain.ETHEREUM:
        return None
    return ETHADDRESS_TO_KNOWN_NAME.get(address, None)


def token_mappings_address_to_name(
        _: DBHandler,
        address: ChecksumEvmAddress,
        blockchain: SupportedBlockchain,  # pylint: disable=unused-argument
) -> Optional[str]:
    """Returns the token name for a token address in the global database or None
    if the address is no token address
    """
    token_mappings = GlobalDBHandler().get_tokens_mappings(addresses=[address])
    return token_mappings.get(address, None)


def ens_address_to_name(
        db: DBHandler,
        address: ChecksumEvmAddress,
        blockchain: SupportedBlockchain,
) -> Optional[str]:
    """Returns the ens name for an address or None if the address doesn't have one"""
    if blockchain != SupportedBlockchain.ETHEREUM:
        return None

    db_ens = DBEns(db)
    with db.conn.read_ctx() as cursor:
        db_reverse_ens = db_ens.get_reverse_ens(
            cursor=cursor,
            addresses=[address],
        )
        address_ens = db_reverse_ens.get(address, None)
        if isinstance(address_ens, EnsMapping):
            return address_ens.name

        return None
