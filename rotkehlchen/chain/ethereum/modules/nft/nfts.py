import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Optional

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.filtering import NFTFilterQuery
from rotkehlchen.db.settings import CachedSettings
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
    str | None,  # name
    str | None,  # price_in_asset
    str | None,  # price_asset
    bool,  # whether the price is manually input
    ChecksumEvmAddress,  # owner address
    bool,  # whether is an lp
    str | None,  # image_url
    str | None,  # collection_name
]
NFT_DB_READ_TUPLE = tuple[
    str,  # identifier
    str | None,  # name
    str | None,  # price_in_asset
    str | None,  # price_asset
    bool,  # whether the price is manually input
    bool,  # whether is an lp
    str | None,  # image_url
    str | None,  # collection_name
]


def _deserialize_nft_price(last_price: str, last_price_asset: str) -> tuple[FVal, Asset, FVal]:
    """Deserialize last price and last price asset from a DB entry
    """
    price_in_asset = deserialize_fval_or_zero(value=last_price, name='price_in_asset', location='nft_tuple')  # noqa: E501
    # find_usd_price should be fast here since in most cases price should be cached
    usd_price = price_in_asset * Inquirer.find_usd_price(price_asset := Asset(last_price_asset))
    return price_in_asset, price_asset, usd_price


def _deserialize_nft_from_db(
        entry: NFT_DB_READ_TUPLE,
        price_tuple: tuple[FVal, Asset, FVal],
) -> dict[str, Any]:
    """From a db tuple extract the information required by the API for an NFT.
    It requires a tuple with the price in the asset used to value the nft,
    the asset used to value the nft and the usd price of the nft.
    """
    price_in_asset, price_asset, usd_price = price_tuple
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
        self.opensea = Opensea(
            database=database,
            msg_aggregator=msg_aggregator,
            ethereum_inquirer=ethereum_inquirer,
        )

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
        """Gets info for all NFTs of the given addresses.
        Used by rest API get_nfts.

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
        total_usd_value = ZERO
        query, bindings = filter_query.prepare(with_pagination=False)
        usd_to_main_currency_rate = ONE if CachedSettings().main_currency == A_USD else Inquirer.find_main_currency_price(A_USD)  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            entries_total = cursor.execute('SELECT COUNT(*) FROM nfts').fetchone()[0]
            entries_found = 0
            usd_price_tuples = {}  # store the queried prices and calculated usd price
            cursor.execute(
                'SELECT last_price, last_price_asset, identifier FROM nfts ' + query,
                bindings,
            )
            for db_entry in cursor:  # we do this query because the previous one is limited to the page and we need to query the total usd price  # noqa: E501
                price_in_asset, price_asset, usd_price = _deserialize_nft_price(
                    last_price=db_entry[0],
                    last_price_asset=db_entry[1],
                )
                usd_price_tuples[db_entry[2]] = (price_in_asset, price_asset, usd_price)  # save all the prices to reuse them when creating the response  # noqa: E501
                total_usd_value += usd_price
                entries_found += 1

        with self.db.user_write() as write_ctx:
            write_ctx.executemany(
                'UPDATE nfts SET usd_price=? WHERE identifier=?',
                [(float(price_tuple[2]), ident) for ident, price_tuple in usd_price_tuples.items()],  # noqa: E501
            )  # update the usd price since the consumer of the api always sorts by usd price

        query, bindings = filter_query.prepare()
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(  # this sometimes causes https://github.com/rotki/rotki/issues/5432
                'SELECT identifier, name, last_price, last_price_asset, manual_price, is_lp, '
                'image_url, collection_name FROM nfts ' + query,
                bindings,
            )
            entries = []
            for x in cursor:
                entry_dict = _deserialize_nft_from_db(entry=x, price_tuple=usd_price_tuples[x[0]])
                entry_dict['price'] = entry_dict.pop('usd_price') * usd_to_main_currency_rate
                entries.append(entry_dict)

        return {
            'entries': entries,
            'entries_found': entries_found,
            'entries_total': entries_total,
            'total_value': total_usd_value * usd_to_main_currency_rate,
        }

    def query_balances(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> None:
        """Queries NFT balances for the specified addresses and saves them to the db.
        Doesn't return anything. The actual opensea querying part is protected by a lock.

        May raise:
        - RemoteError
        """
        with self.db.conn.read_ctx() as cursor:
            accounts = self.db.get_blockchain_accounts(cursor=cursor)
        # Be sure that the only addresses queried already exist in the database. Fix for #4456
        queried_addresses = sorted(set(accounts.eth) & set(addresses))  # Sorting for consistency in tests  # noqa: E501
        nft_results, _ = self._get_all_nft_data(queried_addresses, ignore_cache=True)
        db_data: list[NFT_DB_WRITE_TUPLE] = []
        for address, nfts in nft_results.items():
            for nft in nfts:
                collection_name = nft.collection.name if nft.collection is not None else None
                if collection_name == 'Uniswap V3 Positions':  # skip all uniswap v3 positions - they are handled by UniswapV3Balances now.  # noqa: E501
                    continue
                db_data.append((nft.token_identifier, nft.name, str(nft.price_in_asset), nft.price_asset.identifier, False, address, False, nft.image_url, collection_name))  # noqa: E501

        # Update DB cache
        fresh_nfts_identifiers = [x[0] for x in db_data]
        with self.db.user_write() as write_cursor:
            # Remove NFTs that the user no longer owns from the DB cache
            write_cursor.execute(
                f'DELETE FROM nfts WHERE owner_address IN '
                f'({",".join("?" * len(addresses))}) AND identifier NOT IN '
                f'({",".join("?" * len(fresh_nfts_identifiers))})',
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
            identifier: str | None = None,
            lps_handling: NftLpHandling = NftLpHandling.ALL_NFTS,
            from_asset: Asset | None = None,
            to_asset: Asset | None = None,
            only_with_manual_prices: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Queries database for prices of NFTs.
        When only manual prices are returned the price of the reference asset is not queried.
        If an identifier is provided returns the information related to that identifier only.

        If only_with_manual_prices is set to True then the price is not queried for each nft
        and the price field is set to None.
        """
        filter_query = NFTFilterQuery.make(
            lps_handling=lps_handling,
            nft_id=from_asset.identifier if from_asset is not None else identifier,
            last_price_asset=to_asset,
            only_with_manual_prices=only_with_manual_prices,
        )
        query, bindings = filter_query.prepare()
        query_str = 'SELECT identifier, last_price, last_price_asset, manual_price from nfts ' + query  # noqa: E501

        main_currency = CachedSettings().main_currency
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
                    'price': None,
                }

                if only_with_manual_prices is True:
                    # if we don't need the price don't query it
                    result.append(entry_info)
                    continue

                # query the price in main currency and update it in entry_info
                if target_asset != main_currency:
                    try:
                        to_asset_main_currency_price = Inquirer.find_main_currency_price(target_asset)  # noqa: E501
                    except RemoteError as e:
                        log.error(
                            f'Error querying current price of {target_asset} in custom nft '
                            f'price api call due to {e!s}. Ignoring.',
                        )
                        continue
                    if to_asset_main_currency_price == ZERO:
                        log.error(
                            f'Could not find current price for {target_asset} in custom nft '
                            f'price api call. Ignoring.',
                        )
                        continue
                    price = to_asset_main_currency_price * FVal(entry[1])
                else:  # target_asset == main_currency
                    price = entry[1]

                entry_info['price'] = str(price)
                result.append(entry_info)

        return result

    def add_nft_with_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            price: Price,
    ) -> bool:
        """
        Only used by rest API add_manual_latest_price
        May raise:
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
        """This is only used by rest API delete_manual_latest_price"""
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
