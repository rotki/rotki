import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, NamedTuple, Optional, Tuple

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.uniswap.v3.types import AddressToUniswapV3LPBalances
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.externalapis.opensea import NFT, Opensea
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn, cache_response_timewise_immutable
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FREE_NFT_LIMIT = 10


class NFTResult(NamedTuple):
    addresses: Dict[ChecksumEvmAddress, List[NFT]]
    entries_found: int
    entries_limit: int

    def serialize(self) -> Dict[str, Any]:
        return {
            'addresses': {address: [x.serialize() for x in nfts] for address, nfts in self.addresses.items()},  # noqa: E501
            'entries_found': self.entries_found,
            'entries_limit': self.entries_limit,
        }


class Nfts(EthereumModule, CacheableMixIn, LockableQueryMixIn):  # lgtm [py/missing-call-to-init]

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional['Premium'],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__()
        self.msg_aggregator = msg_aggregator
        self.db = database
        self.ethereum = ethereum_manager
        self.premium = premium
        self.opensea = Opensea(database=database, msg_aggregator=msg_aggregator)

    @protect_with_lock()
    @cache_response_timewise_immutable()
    def _get_all_nft_data(
            self,  # pylint: disable=unused-argument
            addresses: List[ChecksumEvmAddress],
            # Kwargs here is so linters don't complain when the "magic" ignore_cache kwarg is given
            **kwargs: Any,
    ) -> Tuple[Dict[ChecksumEvmAddress, List[NFT]], int]:
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
            addresses: List[ChecksumEvmAddress],
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

    def get_balances(
            self,
            addresses: List[ChecksumEvmAddress],
            uniswap_nfts: Optional[AddressToUniswapV3LPBalances],
            return_zero_values: bool,
            ignore_cache: bool,
    ) -> Dict[ChecksumEvmAddress, List[Dict[str, Any]]]:
        """Gets all NFT balances. The actual opensea querying part is protected by a lock.
        If `uniswap_nfts` is not None then the worth of the LPs are used as the value of the NFTs.
        If `return_zero_values` is False then zero value NFTs are not returned in the result.

        May raise:
        - RemoteError
        """
        with self.db.conn.read_ctx() as cursor:
            accounts = self.db.get_blockchain_accounts(cursor=cursor)
        # Be sure that the only addresses queried already exist in the database. Fix for #4456
        queried_addresses = list(set(accounts.eth) & set(addresses))
        result: DefaultDict[ChecksumEvmAddress, List[Dict[str, Any]]] = defaultdict(list)
        _nft_results, _ = self._get_all_nft_data(queried_addresses, ignore_cache=ignore_cache)
        # the filtering happens outside `_get_all_nft_data` to avoid invalidating the cache on
        # every addition/removal to ignored nfts
        nft_results = self._filter_ignored_nfts(_nft_results)
        cached_db_result = self.get_nfts_with_price()
        cached_db_prices = {x['asset']: x for x in cached_db_result}
        db_data: List[Tuple[str, Optional[str], Optional[str], Optional[str], int, ChecksumEvmAddress]] = []  # noqa: E501
        # get uniswap v3 lp balances and update nfts that are LPs with their worths.
        for address, nfts in nft_results.items():
            for nft in nfts:
                cached_price_data = cached_db_prices.get(nft.token_identifier)
                # get the lps for the address and check if the nft is a LP,
                # then replace the worth with LP value.
                uniswap_v3_lps = uniswap_nfts.get(address) if uniswap_nfts is not None else None
                uniswap_v3_lp = next((entry for entry in uniswap_v3_lps if entry.nft_id == nft.token_identifier), None) if uniswap_v3_lps is not None else None  # noqa:E501
                if uniswap_v3_lp is not None:
                    result[address].append({
                        'id': nft.token_identifier,
                        'name': nft.name,
                        'collection_name': nft.collection.name if nft.collection is not None else None,  # noqa: E501
                        'manually_input': False,
                        'price_asset': 'USD',
                        'price_in_asset': uniswap_v3_lp.user_balance.usd_value,
                        'usd_price': uniswap_v3_lp.user_balance.usd_value,
                        'image_url': nft.image_url,
                        'is_lp': True,
                    })
                    db_data.append((nft.token_identifier, nft.name, str(uniswap_v3_lp.user_balance.usd_value), 'USD', 0, address))  # noqa: E501
                elif cached_price_data is not None and cached_price_data['manually_input']:
                    result[address].append({
                        'id': nft.token_identifier,
                        'name': nft.name,
                        'collection_name': nft.collection.name if nft.collection is not None else None,  # noqa: E501
                        'manually_input': True,
                        'price_asset': cached_price_data['price_asset'],
                        'price_in_asset': FVal(cached_price_data['price_in_asset']),
                        'usd_price': FVal(cached_price_data['usd_price']),
                        'image_url': nft.image_url,
                        'is_lp': False,
                    })
                elif nft.price_usd != ZERO:
                    result[address].append({
                        'id': nft.token_identifier,
                        'name': nft.name,
                        'collection_name': nft.collection.name if nft.collection is not None else None,  # noqa: E501
                        'manually_input': False,
                        'price_asset': 'ETH',
                        'price_in_asset': nft.price_eth,
                        'usd_price': nft.price_usd,
                        'image_url': nft.image_url,
                        'is_lp': False,
                    })
                    db_data.append((nft.token_identifier, nft.name, str(nft.price_eth), 'ETH', 0, address))  # noqa: E501
                else:
                    if return_zero_values:
                        result[address].append({
                            'id': nft.token_identifier,
                            'name': nft.name,
                            'collection_name': nft.collection.name if nft.collection is not None else None,   # noqa: E501
                            'manually_input': False,
                            'price_asset': 'USD',
                            'price_in_asset': ZERO,
                            'usd_price': ZERO,
                            'image_url': nft.image_url,
                            'is_lp': False,
                        })
                    # Always write detected nfts in the DB to have name and address associated
                    db_data.append((nft.token_identifier, nft.name, None, None, 0, address))  # noqa: E501
        # save opensea data in the DB
        if len(db_data) != 0:
            with self.db.user_write() as cursor:
                cursor.executemany(
                    'INSERT OR IGNORE INTO assets(identifier) VALUES(?)',
                    [(x[0],) for x in db_data],
                )
                for entry in db_data:
                    exist_result = cursor.execute(
                        'SELECT manual_price FROM nfts WHERE identifier=?',
                        (entry[0],),
                    ).fetchone()
                    if exist_result is None or bool(exist_result[0]) is False:
                        cursor.execute(
                            'INSERT OR IGNORE INTO nfts('
                            'identifier, name, last_price, last_price_asset, manual_price, owner_address'  # noqa: E501
                            ') VALUES(?, ?, ?, ?, ?, ?)',
                            entry,
                        )

        return result

    def get_nfts_with_price(self, identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Given an identifier for an nft asset return information about its manual price and
        price queried.
        """
        query_str = 'SELECT identifier, last_price, last_price_asset, manual_price from nfts WHERE last_price IS NOT NULL'  # noqa: E501
        bindings = []
        if identifier is not None:
            query_str += ' AND identifier=?'
            bindings.append(identifier)

        with self.db.conn.read_ctx() as cursor:
            query = cursor.execute(query_str, bindings)
            result = []
            for entry in query:
                to_asset_id = entry[2] if entry[2] is not None else A_USD
                try:
                    to_asset = Asset(to_asset_id).check_existence()
                except UnknownAsset:
                    log.error(
                        f'Unknown asset {to_asset_id} in custom nft price DB table. Ignoring.',
                    )
                    continue

                if to_asset != A_USD:
                    try:
                        to_asset_usd_price = Inquirer().find_usd_price(to_asset)
                    except RemoteError as e:
                        log.error(
                            f'Error querying current usd price of {to_asset} in custom nft price '
                            f'api call due to {str(e)}. Ignoring.',
                        )
                        continue
                    if to_asset_usd_price == ZERO:
                        log.error(
                            f'Could not find current usd price for {to_asset} in custom nft '
                            f'price api call. Ignoring.',
                        )
                        continue
                    usd_price = to_asset_usd_price * FVal(entry[1])
                else:  # to_asset == USD
                    usd_price = entry[1]

                result.append({
                    'asset': entry[0],
                    'manually_input': bool(entry[3]),
                    'price_asset': to_asset_id,
                    'price_in_asset': entry[1],
                    'usd_price': str(usd_price),
                })

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
                raise InputError(f'Failed to write price for {from_asset.identifier} due to {str(e)}') from e  # noqa: E501

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
                raise InputError(f'Failed to delete price for {asset.identifier} due to {str(e)}') from e  # noqa: E501
            if cursor.rowcount != 1:
                raise InputError(f'Failed to delete price for unknown asset {asset.identifier}')

        return True

    def _filter_ignored_nfts(self, nfts_data: Dict[ChecksumEvmAddress, List[NFT]]) -> Dict[ChecksumEvmAddress, List[NFT]]:  # noqa: E501
        """Remove ignored NFTs from NFTs data."""
        with self.db.conn.read_ctx() as cursor:
            # convert to set to allow O(1) during `in` conditional below.
            ignored_nfts = set(self.db.get_ignored_assets(cursor=cursor, only_nfts=True))

        for address, nfts in nfts_data.items():
            nfts_data[address] = [x for x in nfts if x.token_identifier not in ignored_nfts]

        return nfts_data

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
