import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Optional

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import AddressToUniswapV3LPBalances
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.externalapis.opensea import NFT, Opensea
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval_or_zero
from rotkehlchen.types import ChecksumEvmAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise_immutable
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

from .constants import FREE_NFT_LIMIT
from .structures import NftLpHandling, NFTResult

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

NFT_DB_WRITE_TUPLE = tuple[
    str,  # identifier
    Optional[str],  # name
    Optional[str],  # price_in_asset
    Optional[str],  # price_asset
    bool,  # whether the price is manually input
    ChecksumEvmAddress,  # owner address
    bool,  # whether is an lp
    Optional[str],  # image_url
    Optional[str],  # collection_name
]
NFT_DB_READ_TUPLE = tuple[
    str,  # identifier
    Optional[str],  # name
    Optional[str],  # price_in_asset
    Optional[str],  # price_asset
    bool,  # whether the price is manually input
    bool,  # whether is an lp
    Optional[str],  # image_url
    Optional[str],  # collection_name
]


def _deserialize_nft_price(
        last_price: Optional[str],
        last_price_asset: Optional[str],
) -> tuple[FVal, Asset, FVal]:
    """Deserialize last price and last price asset from a DB entry
    TODO: Both last_price and last_price_asset are optional in the current DB schema
    but they are not used as such and should not be. We need to change the schema.
    """
    price_in_asset = deserialize_fval_or_zero(value=last_price, name='price_in_asset', location='nft_tuple')  # noqa: E501
    price_asset = Asset(last_price_asset)  # type: ignore  # due to the asset schema problem
    # find_usd_price should be fast here since in most cases price should be cached
    usd_price = price_in_asset * Inquirer.find_usd_price(price_asset)
    return price_in_asset, price_asset, usd_price


def _deserialize_nft_from_db(entry: NFT_DB_READ_TUPLE) -> dict[str, Any]:
    """From a db tuple extract the information required by the API for a NFT"""
    price_in_asset, price_asset, usd_price = _deserialize_nft_price(
        last_price=entry[2],
        last_price_asset=entry[3],
    )
    return {
        'id': entry[0],
        'name': entry[1],
        'price_in_asset': price_in_asset,
        'price_asset': price_asset,
        'manually_input': bool(entry[4]),
        'is_lp': bool(entry[5]),
        'image_url': entry[6],
        'usd_price': usd_price,
        'collection_name': entry[7],
    }


class Nfts(EthereumModule, CacheableMixIn, LockableQueryMixIn):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional['Premium'],
            msg_aggregator: MessagesAggregator,
    ) -> None:  # avoiding super() since cant't call abstract class's __init__
        CacheableMixIn.__init__(self)
        LockableQueryMixIn.__init__(self)
        self.msg_aggregator = msg_aggregator
        self.db = database
        self.ethereum = ethereum_inquirer
        self.premium = premium
        self.opensea = Opensea(database=database, msg_aggregator=msg_aggregator)

    @protect_with_lock()
    @cache_response_timewise_immutable()
    def _get_all_nft_data(
            self,  # pylint: disable=unused-argument
            addresses: list[ChecksumEvmAddress],
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> tuple[dict[ChecksumEvmAddress, list[NFT]], int]:
        """May raise RemoteError"""
        result = {}
        total_nfts_num = 0
        for address in addresses:
            nfts = self.opensea.get_account_nfts(address)
            nfts_num = len(nfts)
            if nfts_num != 0:
                if self.premium is None:
                    if nfts_num + total_nfts_num > FREE_NFT_LIMIT:
                        remaining_size = FREE_NFT_LIMIT - total_nfts_num
                    else:
                        remaining_size = nfts_num

                    if remaining_size != 0:
                        result[address] = nfts[:remaining_size]
                        total_nfts_num += remaining_size
                        continue

                    break  # else we hit the nft limit so break

                result[address] = nfts
                total_nfts_num += nfts_num
        return result, total_nfts_num

    def get_all_info(
            self,
            addresses: list[ChecksumEvmAddress],
            ignore_cache: bool,
    ) -> NFTResult:
        """Gets info for all NFTs of the given addresses

        Returns a tuple with:
        - Mapping of addresses to list of NFTs
        - Total NFTs found - integer
        - Limit for free NFTs - integer

        May raise:
        - RemoteError
        """
        result, total_nfts_num = self._get_all_nft_data(addresses, ignore_cache=ignore_cache)
        # the filtering happens outside `_get_all_nft_data` to avoid invalidating the cache on
        # every addition/removal to ignored nfts
        result = self._filter_ignored_nfts(result)

        return NFTResult(
            addresses=result,
            entries_found=total_nfts_num,
            entries_limit=FREE_NFT_LIMIT,
        )

    def get_db_nft_balances(self, filter_query: 'NFTFilterQuery') -> dict[str, Any]:
        """Filters (with `filter_query`) and returns cached nft balances in the nfts table"""
        query, bindings = filter_query.prepare()
        total_usd_value = ZERO
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(  # this sometimes causes https://github.com/rotki/rotki/issues/5432
                'SELECT identifier, name, last_price, last_price_asset, manual_price, is_lp, '
                'image_url, collection_name FROM nfts ' + query,
                bindings,
            )
            entries = [_deserialize_nft_from_db(x) for x in cursor]
            query, bindings = filter_query.prepare(with_pagination=False)
            cursor.execute(
                'SELECT last_price, last_price_asset FROM nfts ' + query,
                bindings,
            )
            entries_found = 0
            for db_entry in cursor:
                _, _, usd_price = _deserialize_nft_price(
                    last_price=db_entry[0],
                    last_price_asset=db_entry[1],
                )
                total_usd_value += usd_price
                entries_found += 1
            entries_total = cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0]

        return {
            'entries': entries,
            'entries_found': entries_found,
            'entries_total': entries_total,
            'total_usd_value': total_usd_value,
        }

    def query_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            uniswap_nfts: Optional[AddressToUniswapV3LPBalances],
    ) -> None:
        """Queries NFT balances for the specified addresses and saves them to the db.
        Doesn't return anything. The actual opensea querying part is protected by a lock.
        If `uniswap_nfts` is not None then the worth of the LPs are used as the value of the NFTs.

        May raise:
        - RemoteError
        """
        with self.db.conn.read_ctx() as cursor:
            accounts = self.db.get_blockchain_accounts(cursor=cursor)
        # Be sure that the only addresses queried already exist in the database. Fix for #4456
        queried_addresses = sorted(set(accounts.eth) & set(addresses))  # Sorting for consistency in tests  # noqa: E501
        nft_results, _ = self._get_all_nft_data(queried_addresses, ignore_cache=True)
        db_data: list[NFT_DB_WRITE_TUPLE] = []
        # get uniswap v3 lp balances and update nfts that are LPs with their worth.
        for address, nfts in nft_results.items():
            for nft in nfts:
                # get the lps for the address and check if the nft is a LP,
                # then replace the worth with LP value.
                uniswap_v3_lps = uniswap_nfts.get(address) if uniswap_nfts is not None else None
                uniswap_v3_lp = next((entry for entry in uniswap_v3_lps if entry.nft_id == nft.token_identifier), None) if uniswap_v3_lps is not None else None  # noqa: E501
                collection_name = nft.collection.name if nft.collection is not None else None
                if uniswap_v3_lp is not None:
                    db_data.append((nft.token_identifier, nft.name, str(uniswap_v3_lp.user_balance.usd_value), 'USD', False, address, True, nft.image_url, collection_name))  # noqa: E501
                else:
                    db_data.append((nft.token_identifier, nft.name, str(nft.price_eth), 'ETH', False, address, False, nft.image_url, collection_name))  # noqa: E501

        # Update DB cache
        fresh_nfts_identifiers = [x[0] for x in db_data]
        with self.db.user_write() as write_cursor:
            # Remove NFTs that the user no longer owns from the DB cache
            write_cursor.execute(
                f'DELETE FROM nfts WHERE owner_address IN '
                f'({",".join("?"*len(addresses))}) AND identifier NOT IN '
                f'({",".join("?"*len(fresh_nfts_identifiers))})',
                tuple(addresses) + tuple(fresh_nfts_identifiers),
            )

            # Add new NFTs to the DB cache
            write_cursor.executemany(
                'INSERT OR IGNORE INTO assets(identifier) VALUES(?)',
                [(x,) for x in fresh_nfts_identifiers],
            )
            write_cursor.executemany(
                'INSERT OR IGNORE INTO nfts('
                'identifier, name, last_price, last_price_asset, manual_price, owner_address, is_lp, image_url, collection_name'  # noqa: E501
                ') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
                db_data,
            )

            # Update NFTs that already exist in the cache. First, update everything except price
            write_cursor.executemany(
                'UPDATE nfts SET name=?, owner_address=?, image_url=?, collection_name=? '
                'WHERE identifier=?',
                [(x[1], x[5], x[7], x[8], x[0]) for x in db_data],
            )
            # Then, update price where it was not manually input.
            # To preserve user manually input price
            write_cursor.executemany(
                'UPDATE nfts SET last_price=?, last_price_asset=? '
                'WHERE identifier=? AND manual_price=0',
                [(x[2], x[3], x[0]) for x in db_data],
            )

    def get_nfts_with_price(
            self,
            identifier: Optional[str] = None,
            lps_handling: NftLpHandling = NftLpHandling.ALL_NFTS,
            from_asset: Optional[Asset] = None,
            to_asset: Optional[Asset] = None,
            only_with_manual_prices: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Queries database for prices of NFTs.
        When only manual prices are returned the usd price of the reference asset is not queried.
        If an identifier is provided returns the information related to that identifier only.

        if only_with_manual_prices is set to True then the usd price is not queried for each nft
        and the usd_price field is set to None.
        """
        filter_query = NFTFilterQuery.make(
            lps_handling=lps_handling,
            nft_id=from_asset.identifier if from_asset is not None else identifier,
            last_price_asset=to_asset,
            only_with_manual_prices=only_with_manual_prices,
        )
        query, bindings = filter_query.prepare()
        query_str = 'SELECT identifier, last_price, last_price_asset, manual_price from nfts ' + query  # noqa: E501

        result = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query_str, bindings)
            for entry in cursor:
                to_asset_id = entry[2] if entry[2] is not None else A_USD.identifier
                try:
                    target_asset = Asset(to_asset_id).check_existence()
                except UnknownAsset:
                    log.error(
                        f'Unknown asset {to_asset_id} in custom nft price DB table. Ignoring.',
                    )
                    continue

                entry_info = {
                    'asset': entry[0],
                    'manually_input': bool(entry[3]),
                    'price_asset': to_asset_id,
                    'price_in_asset': entry[1],
                    'usd_price': None,
                }

                if only_with_manual_prices is True:
                    # if we don't need the usd price don't query it
                    result.append(entry_info)
                    continue

                # query the usd price and update it in entry_info
                if target_asset != A_USD:
                    try:
                        to_asset_usd_price = Inquirer().find_usd_price(target_asset)
                    except RemoteError as e:
                        log.error(
                            f'Error querying current usd price of {target_asset} in custom nft '
                            f'price api call due to {e!s}. Ignoring.',
                        )
                        continue
                    if to_asset_usd_price == ZERO:
                        log.error(
                            f'Could not find current usd price for {target_asset} in custom nft '
                            f'price api call. Ignoring.',
                        )
                        continue
                    usd_price = to_asset_usd_price * FVal(entry[1])
                else:  # to_asset == USD
                    usd_price = entry[1]

                entry_info['usd_price'] = str(usd_price)
                result.append(entry_info)

        return result

    def add_nft_with_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
    ) -> bool:
        """May raise:
         - InputError
        """
        with self.db.user_write() as cursor:
            try:
                cursor.execute(
                    'UPDATE nfts SET last_price=?, last_price_asset=?, manual_price=? '
                    'WHERE identifier=?',
                    (str(price), to_asset.identifier, 1, from_asset.identifier),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Failed to write price for {from_asset.identifier} due to {e!s}') from e  # noqa: E501

            if cursor.rowcount != 1:
                raise InputError(f'Failed to write price for {from_asset.identifier}')

        return True

    def delete_price_for_nft(self, asset: Asset) -> bool:
        with self.db.user_write() as cursor:
            try:
                cursor.execute(
                    'UPDATE nfts SET last_price=?, last_price_asset=? WHERE identifier=?',
                    (None, None, asset.identifier),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Failed to delete price for {asset.identifier} due to {e!s}') from e  # noqa: E501
            if cursor.rowcount != 1:
                raise InputError(f'Failed to delete price for unknown asset {asset.identifier}')

        return True

    def _filter_ignored_nfts(self, nfts_data: dict[ChecksumEvmAddress, list[NFT]]) -> dict[ChecksumEvmAddress, list[NFT]]:  # noqa: E501
        """Remove ignored NFTs from NFTs data."""
        with self.db.conn.read_ctx() as cursor:
            ignored_nft_ids = self.db.get_ignored_asset_ids(cursor=cursor, only_nfts=True)

        for address, nfts in nfts_data.items():
            nfts_data[address] = [x for x in nfts if x.token_identifier not in ignored_nft_ids]

        return nfts_data

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
