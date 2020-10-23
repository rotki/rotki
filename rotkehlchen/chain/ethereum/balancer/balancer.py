import logging
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Set,
)

from eth_utils import to_checksum_address
import gevent

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.constants import ZERO

from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from .graph import (
    POOLSHARES_QUERY,
    TOKENPRICES_QUERY,
    SWAPS_QUERY,
    SWAPS_QUERY_FILTERING_BY_TS_GTE,
)
from .typing import (
    AddressesBalancerPools,
    AddressesBalancerTrades,
    AssetsPrices,
    BalancerBalances,
    BalancerPoolAsset,
    BalancerPoolAssets,
    BalancerPool,
    BalancerPools,
    BalancerTrade,
    DDAddressesBalancerPools,
    KnownAsset,
    UnknownEthereumToken,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)

BALANCER_TRADES_PREFIX = 'balancer_trades'


class Balancer(EthereumModule):
    """Balancer integration module

    https://docs.balancer.finance/
    https://github.com/balancer-labs/balancer-subgraph
    """
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.graph = Graph(
            'https://api.thegraph.com/subgraphs/name/balancer-labs/balancer',
        )

    def _convert_addresses_to_lower_case(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> List[str]:
        return [address.lower() for address in addresses]

    # Get balances private methods

    def _get_balances(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> BalancerBalances:
        """Get the addresses' pools data querying the Balancer subgraph

        Query
        -----
        Get list of poolShares filtering by address and balance

            * Addresses must be lower case, no support for checksum ones
            * Balance gt 0

        Response process highlights
        ---------------------------
        Per each poolShare token:

            * Try to get its <Asset> (by symbol) and classify the token as
            "known" or "unknown".
            * Calculate the estimated balance of the underlying token
            (e.g. WETH, BAL) given the address pool shares balance (i.e. BPTs).
            * Store any Ethereum address as a checksum address.
            * Create as many <BalancerPoolAsset> as underlying tokens, and
            create the <BalancerPool>.
            * Return <BalancerBalances> which contains the map address - pools
            balances map, and the known/unknown sets.
        """
        # ! Format addresses, The Graph does not support checksum addresses
        addresses_lower = self._convert_addresses_to_lower_case(addresses)
        param_types = {
            '$addresses': '[String!]',
            '$balance': 'BigDecimal!',
        }
        param_values = {
            'addresses': addresses_lower,
            'balance': "0",
        }
        result = self.graph.query(
            querystr=POOLSHARES_QUERY.format(),  # ! Remove returns in string
            param_types=param_types,
            param_values=param_values,
        )
        addresses_balancer_pools: DDAddressesBalancerPools = defaultdict(list)
        known_assets: Set[KnownAsset] = set()
        unknown_assets: Set[ChecksumEthAddress] = set()
        for pool_share in result['poolShares']:
            # ! Checksum address
            address = to_checksum_address(pool_share['userAddress']['id'])
            user_pool_balance = FVal(pool_share['balance'])
            pool = pool_share['poolId']
            pool_balance = FVal(pool['totalShares'])

            bpool_assets = []
            for token in pool['tokens']:
                # Try to get the token <Asset> and classify as known or unknown
                # ! Checksum address
                token_address = to_checksum_address(token['address'])
                token_symbol = token['symbol']
                asset = None
                try:
                    # ! TODO VN PR: need optimisations? symbol uniqueness?
                    asset = Asset(token_symbol)
                except UnknownAsset:
                    unknown_assets.add(token_address)
                    log.error(f'Encountered unknown asset {token_symbol} in balancer. Skipping')
                else:
                    known_assets.add(KnownAsset(address=token_address, asset=asset))

                # Estimate underlying asset balance given user pool balance
                asset_balance = FVal(token['balance'])
                user_asset_balance = (user_pool_balance / pool_balance * asset_balance)

                bpool_asset = BalancerPoolAsset(
                    address=token_address,
                    balance=asset_balance,
                    denorm_weight=FVal(token['denormWeight']),
                    name=token['name'],
                    symbol=token_symbol,
                    user_balance=user_asset_balance,
                    asset=asset,
                )
                bpool_assets.append(bpool_asset)

            bpool = BalancerPool(
                address=to_checksum_address(pool['id']),  # ! Checksum address
                assets=bpool_assets,
                assets_count=FVal(pool['tokensCount']),
                symbol=pool['symbol'],
                balance=pool_balance,
                weight=FVal(pool['totalWeight']),
                user_balance=user_pool_balance,
            )
            addresses_balancer_pools[address].append(bpool)

        return BalancerBalances(
            addresses_balancer_pools=addresses_balancer_pools,
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )

    def _get_known_assets_prices(
        self,
        known_assets: Set[KnownAsset],
        unknown_assets: Set[ChecksumEthAddress],
    ) -> AssetsPrices:
        """Get the tokens prices via Inquirer

        Given an asset, if `find_usd_price()` returns zero, it will be added
        into `unknown_assets`.
        """
        known_asset_prices: AssetsPrices = {}
        known_assets_ = list(known_assets)  # ! Get a deterministic sequence
        # ! TODO VN PR: consider timeout and list/kill greenlets
        assets_usd_prices = [
            gevent.spawn(Inquirer().find_usd_price, known_asset.asset)
            for known_asset in known_assets_
        ]
        gevent.joinall(assets_usd_prices, timeout=5)

        for known_asset, asset_usd_price in zip(known_assets_, assets_usd_prices):
            if asset_usd_price.value != Price(ZERO):
                known_asset_prices[known_asset.address] = FVal(asset_usd_price.value)
            else:
                unknown_assets.add(known_asset.address)

        return known_asset_prices

    def _get_unknown_assets_prices(
            self,
            unknown_assets: Set[ChecksumEthAddress],
    ) -> AssetsPrices:
        """Get the tokens prices via the Balancer subgraph

        Query
        -----
        Get list of tokenPrices filtering by token id

        # ! TODO VN PR
        # ! Add USD value per asset, either via Inquirer or The Graph
        # ! Add Asset instance per asset, at least if exists
        """
        unknown_assets_prices: AssetsPrices = {}
        # ! Format addresses, The Graph does not support checksum addresses
        token_addresses = self._convert_addresses_to_lower_case(unknown_assets)
        param_types = {
            '$token_ids': '[ID!]',
        }
        param_values = {
            'token_ids': token_addresses,
        }
        result = self.graph.query(
            querystr=TOKENPRICES_QUERY.format(),  # ! Remove returns in string
            param_types=param_types,
            param_values=param_values,
        )
        # ! Checksum address
        unknown_assets_prices = {
            to_checksum_address(token['id']): FVal(token['price'])
            for token in result['tokenPrices']
        }
        return unknown_assets_prices

    def _update_assets_prices_in_addresses_balancer_pools(
            self,
            addresses_balancer_pools: AddressesBalancerPools,
            known_assets_prices: AssetsPrices,
            unknown_assets_prices: AssetsPrices,
    ) -> AddressesBalancerPools:
        """Update the pools underlying assets prices in USD (prices obtained
        via Inquirer and the Balancer subgraph)

        Process highlights
        ------------------
        Per each <BalancerPoolAsset> in <BalancerPool>.assets:
            * Replace <BalancerPoolAsset> including the asset USD price if it
            exists either in `known_assets_prices` or `unknown_assets_prices`.
            * Replace <BalancerPool> if any underlying asset has been replaced.
        """
        updated_addresses_balancer_pools: AddressesBalancerPools = {}
        for address, balancer_pools in addresses_balancer_pools.items():
            updated_balancer_pools: BalancerPools = []
            for balancer_pool in balancer_pools:
                updated_balancer_pool_assets: BalancerPoolAssets = []
                is_updated = False
                # Try to get price from either known or unknown assets prices.
                # Otherwise keep existing price (zero)
                # ! Assets prices values are <FVal> (truthy)
                for asset in balancer_pool.assets:
                    if asset.address in known_assets_prices:
                        asset_usd = known_assets_prices[asset.address]
                    elif asset.address in unknown_assets_prices:
                        asset_usd = unknown_assets_prices[asset.address]
                    else:
                        asset_usd = ZERO

                    # Replace <BalancerPoolAsset> if asset USD price exists
                    if asset_usd != ZERO:
                        updated_balancer_pool_asset = asset._replace(
                            asset_usd=asset_usd,
                            user_balance_usd=asset.user_balance * asset_usd,
                        )
                        is_updated = True
                    else:
                        updated_balancer_pool_asset = asset

                    updated_balancer_pool_assets.append(updated_balancer_pool_asset)

                # Replace <BalancerPool> if any <BalancerPoolAsset> was replaced
                updated_balancer_pool = (
                    balancer_pool._replace(assets=updated_balancer_pool_assets)
                    if is_updated else balancer_pool
                )
                updated_balancer_pools.append(updated_balancer_pool)

            updated_addresses_balancer_pools[address] = updated_balancer_pools

        return updated_addresses_balancer_pools

    # Get history private methods

    def _get_balancer_trade(
            self,
            address: ChecksumEthAddress,
            trade: Dict,
    ) -> BalancerTrade:
        """Given a trade (swap) dict, returns an instance of BalancerTrade"""
        # Get transaction hash and log index from swap.id
        tx_hash, log_index = trade['id'].split('-')

        asset_in_address = to_checksum_address(trade['tokenIn'])
        asset_in_symbol = trade['tokenInSym']
        asset_out_address = to_checksum_address(trade['tokenOut'])
        asset_out_symbol = trade['tokenOutSym']

        asset_in, asset_out = None, None
        is_asset_in_unknown = False
        is_asset_out_unknown = False
        # Process asset in either as EthereumToken or UnknownEthereumToken
        try:
            asset_in = EthereumToken(asset_in_symbol)
            # Reconvert to UnknownEthereumToken if contract address does not match
            if asset_in.ethereum_address != asset_in_address:
                is_asset_in_unknown = True
                log.error(
                    f'Ethereum token contract address mismatch. '
                    f'Found: {asset_in.ethereum_address}. '
                    f'Expected: {asset_in_address}.',
                )
        except UnknownAsset:
            is_asset_in_unknown = True
            log.error(
                f'Unknown asset_in {asset_in_symbol} with address {asset_in_address} '
                f'in balancer. Instantiating UnknownEthereumToken',
            )
        finally:
            if is_asset_in_unknown:
                asset_in = UnknownEthereumToken(
                    identifier=asset_in_symbol,
                    ethereum_address=asset_in_address,
                )

        # Process asset in either as EthereumToken or UnknownEthereumToken
        try:
            asset_out = EthereumToken(asset_out_symbol)
            # Reconvert to UnknownEthereumToken if contract address does not match
            if asset_out.ethereum_address != asset_out_address:
                is_asset_out_unknown = True
                log.error(
                    f'Ethereum token contract address mismatch. '
                    f'Found: {asset_out.ethereum_address}. '
                    f'Expected: {asset_out_address}.',
                )
        except UnknownAsset:
            is_asset_out_unknown = True
            log.error(
                f'Unknown asset_out {asset_out_symbol} with address {asset_out_address} '
                f'in balancer. Instantiating UnknownEthereumToken',
            )
        finally:
            if is_asset_out_unknown:
                asset_out = UnknownEthereumToken(
                    identifier=asset_out_symbol,
                    ethereum_address=asset_out_address,
                )

        balancer_trade = BalancerTrade(
            tx_hash=tx_hash,
            log_index=int(log_index),
            address=address,
            timestamp=trade['timestamp'],
            usd_fee=Price(trade['feeValue']),
            usd_value=Price(trade['value']),
            pool_address=to_checksum_address(trade['poolAddress']['id']),
            pool_name=trade['poolAddress']['name'],
            pool_liquidity=FVal(trade['poolLiquidity']),
            usd_pool_total_swap_fee=Price(trade['poolTotalSwapFee']),
            usd_pool_total_swap_volume=Price(trade['poolTotalSwapVolume']),
            asset_in=asset_in,
            asset_in_amount=FVal(trade['tokenAmountIn']),
            asset_out=asset_out,
            asset_out_amount=FVal(trade['tokenAmountOut']),
        )
        return balancer_trade

    def _get_trades(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> None:
        """Get the latest addresses' trades (swaps) querying the Balancer
        subgraph and store them in DB

        Queries
        -------
        - Get list of swaps filtering by address, sorted by timestamp in
        ascending

        - Get list of swaps filtering by address and timestamp (gte `end_ts`,
        from `used_query_range_balancer_trades_<address>` entry in the
        `used_query_ranges` table.

        Response process highlights
        ---------------------------
        For each address:
          - Request all trades if there was no record of previous requests in
          `used_query_ranges` table. Otherwise request all trades from
          (included) `end_ts`. This current approach has the following flaws:
            * Rely on timestamps (even filtering by `gte`).
            * No pagination. Queries could exceed max. limit of results per query
            and no edges have been defined (e.g. first, after)

          - Instantiate a <BalancerTrade> per swap data.

          - Store address' list of <BalancerTrade> in the DB, and insert or
          update `used_query_range_balancer_trades_<address>` entry with the
          first and last swaps timestamps.
        """
        # ! Format addresses, The Graph does not support checksum addresses
        addresses_lower = self._convert_addresses_to_lower_case(addresses)

        for address, address_lower in zip(addresses, addresses_lower):
            # Get last used query range
            used_query_range_name = f'{BALANCER_TRADES_PREFIX}_{address}'
            trades_range = self.database.get_used_query_range(used_query_range_name)

            # All trades
            if not trades_range:
                param_types = {'$address': 'String!'}
                param_values = {'address': address_lower}
                gql_query = SWAPS_QUERY.format()

            # Trades starting at last used query range
            else:
                param_types = {
                    '$address': 'String!',
                    '$timestamp': 'Int!',
                }
                param_values = {
                    'address': address_lower,
                    'timestamp': trades_range[1],  # end_ts for timestamp_gte
                }
                gql_query = SWAPS_QUERY_FILTERING_BY_TS_GTE.format()

            # Get address' swaps via Balancer subgraph
            result = self.graph.query(
                querystr=gql_query,
                param_types=param_types,
                param_values=param_values,
            )
            # Get swap BalancerTrade
            balancer_trades: List[BalancerTrade] = []
            for trade in result['swaps']:
                balancer_trade = self._get_balancer_trade(address, trade)
                balancer_trades.append(balancer_trade)

            if balancer_trades:
                # Insert or update last used query range
                self.database.update_used_query_range(
                    name=used_query_range_name,
                    start_ts=balancer_trades[0].timestamp,
                    end_ts=balancer_trades[-1].timestamp,  # response order is asc
                )
                # Insert into DB balancer trades
                self.database.add_balancer_trades(address, balancer_trades)

    def _get_db_trades(
            self,
            address: ChecksumEthAddress,
    ) -> List[BalancerTrade]:
        """Get address' balancer trades from DB"""
        db_trades = self.database.get_balancer_trades(address)
        # ? Sort asc or desc
        db_trades.sort(key=lambda trade: trade.timestamp)

        return db_trades

    def get_balances(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> AddressesBalancerPools:
        """Get the addresses' balances in the Balancer protocol
        """
        balancer_balances = self._get_balances(addresses)

        known_assets = balancer_balances.known_assets
        unknown_assets = balancer_balances.unknown_assets

        known_assets_prices = self._get_known_assets_prices(known_assets, unknown_assets)
        unknown_assets_prices = self._get_unknown_assets_prices(unknown_assets)

        updated_addresses_balancer_pools = (
            self._update_assets_prices_in_addresses_balancer_pools(
                balancer_balances.addresses_balancer_pools,
                known_assets_prices,
                unknown_assets_prices,
            )
        )
        return updated_addresses_balancer_pools

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, Dict]:
        """Get the addresses' history in the Balancer protocol

        Currently, this funcion only returns trades (swaps)
        """
        addresses_trades_history: AddressesBalancerTrades = {}

        # Fetch addresses' last trades from Balancer, and store them in DB
        self._get_trades(addresses)

        for address in addresses:
            # Fetch addresses' trades from DB
            addresses_trades_history[address] = self._get_db_trades(address)

        return {'trades': addresses_trades_history}

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
