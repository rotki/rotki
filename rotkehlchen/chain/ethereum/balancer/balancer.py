import logging
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    Set,
)

from eth_utils import to_checksum_address
import gevent

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.balancer.graph_queries import (
    POOLSHARES_QUERY,
    TOKENPRICES_QUERY,
)
from rotkehlchen.chain.ethereum.balancer.typing import (
    AddressesBalancerPools,
    AssetsPrices,
    BalancerBalances,
    BalancerPoolAsset,
    BalancerPoolAssets,
    BalancerPool,
    BalancerPools,
    DDAddressesBalancerPools,
    KnownAsset,
)
from rotkehlchen.chain.ethereum.graph import Graph
from rotkehlchen.constants import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

log = logging.getLogger(__name__)


class Balancer(EthereumModule):
    """Balancer integration module

    https://docs.balancer.finance/
    https://github.com/balancer-labs/balancer-subgraph
    """
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
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
        addresses_lower = [address.lower() for address in addresses]
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
        token_addresses = [address.lower() for address in unknown_assets]
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

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
