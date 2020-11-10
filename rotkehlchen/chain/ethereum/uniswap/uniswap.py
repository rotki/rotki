import logging
from datetime import datetime, time
from typing import (
    Callable,
    List,
    Optional,
    Set,
    TYPE_CHECKING,
)

from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.assets.utils import get_ethereum_token
from rotkehlchen.chain.ethereum.graph import (
    GRAPH_QUERY_LIMIT,
    format_query_indentation,
    Graph,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from .graph import (
    LIQUIDITY_POSITIONS_QUERY,
    TOKEN_DAY_DATAS_QUERY,
)
from .typing import (
    AddressBalances,
    AssetPrice,
    LiquidityPool,
    LiquidityPoolAsset,
    ProtocolBalance,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)


class Uniswap(EthereumModule):
    """Uniswap integration module

    * Uniswap subgraph:
    https://github.com/Uniswap/uniswap-v2-subgraph
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
        try:
            self.graph: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
            )
        except RemoteError as e:
            self.graph = None
            self.msg_aggregator.add_error(
                f'Could not initialize the Uniswap subgraph due to {str(e)}. '
                f'All uniswap historical queries are not functioning until this is fixed. '
                f'Probably will get fixed with time. If not report it to Rotkis support channel ',
            )

    @staticmethod
    def _get_balances_graph(
        addresses: List[ChecksumEthAddress],
        graph_query: Callable,
    ) -> ProtocolBalance:
        """Get the addresses' pools data querying the Uniswap subgraph
        """
        address_balances: AddressBalances = {address: [] for address in addresses}
        known_assets: Set[EthereumToken] = set()
        unknown_assets: Set[UnknownEthereumToken] = set()

        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(LIQUIDITY_POSITIONS_QUERY.format())
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[String!]',
            '$balance': 'BigDecimal!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'addresses': addresses_lower,
            'balance': "0",
        }
        while True:
            result = graph_query(
                querystr=querystr,
                param_types=param_types,
                param_values=param_values,
            )
            result_data = result['liquidityPositions']

            for lp in result_data:
                user_address = to_checksum_address(lp['user']['id'])
                user_lp_balance = FVal(lp['liquidityTokenBalance'])
                lp_pair = lp['pair']
                lp_address = to_checksum_address(lp_pair['id'])
                lp_total_supply = FVal(lp_pair['totalSupply'])

                # Insert LP tokens reserves within tokens dicts
                token0 = lp_pair['token0']
                token0['total_amount'] = lp_pair['reserve0']
                token1 = lp_pair['token1']
                token1['total_amount'] = lp_pair['reserve1']

                liquidity_pool_assets = []

                for token in token0, token1:
                    # Get the token <EthereumToken> or <UnknownEthereumToken>
                    asset = get_ethereum_token(
                        symbol=token['symbol'],
                        ethereum_address=to_checksum_address(token['id']),
                        name=token['name'],
                        decimals=int(token['decimals']),
                    )

                    # Classify the asset either as known or unknown
                    if isinstance(asset, EthereumToken):
                        known_assets.add(asset)
                    elif isinstance(asset, UnknownEthereumToken):
                        unknown_assets.add(asset)

                    # Estimate the underlying asset total_amount
                    asset_total_amount = FVal(token['total_amount'])
                    user_asset_balance = (
                        user_lp_balance / lp_total_supply * asset_total_amount
                    )

                    liquidity_pool_asset = LiquidityPoolAsset(
                        asset=asset,
                        total_amount=asset_total_amount,
                        user_balance=Balance(amount=user_asset_balance),
                    )
                    liquidity_pool_assets.append(liquidity_pool_asset)

                liquidity_pool = LiquidityPool(
                    address=lp_address,
                    assets=liquidity_pool_assets,
                    total_supply=lp_total_supply,
                    user_balance=Balance(amount=user_lp_balance),
                )
                address_balances[user_address].append(liquidity_pool)

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        protocol_balance = ProtocolBalance(
            address_balances=address_balances,
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )
        return protocol_balance

    @staticmethod
    def _get_balances_chain(addresses: List[ChecksumEthAddress]) -> ProtocolBalance:
        """Get the addresses' pools data via Zerion SDK.
        """
        address_balances: AddressBalances = {address: [] for address in addresses}
        known_assets: Set[EthereumToken] = set()
        unknown_assets: Set[UnknownEthereumToken] = set()

        protocol_balance = ProtocolBalance(
            address_balances=address_balances,
            known_assets=known_assets,
            unknown_assets=unknown_assets,
        )
        return protocol_balance

    @staticmethod
    def _get_known_asset_price(
            known_assets: Set[EthereumToken],
            unknown_assets: Set[UnknownEthereumToken],
            price_query: Callable,
    ) -> AssetPrice:
        """Get the tokens prices via Inquirer

        Given an asset, if `find_usd_price()` returns zero, it will be added
        into `unknown_assets`.
        """
        asset_price: AssetPrice = {}

        for known_asset in known_assets:
            asset_usd_price = price_query(known_asset)

            if asset_usd_price != Price(ZERO):
                asset_price[known_asset.ethereum_address] = asset_usd_price
            else:
                unknown_asset = UnknownEthereumToken(
                    ethereum_address=known_asset.ethereum_address,
                    symbol=known_asset.identifier,
                    name=known_asset.name,
                    decimals=known_asset.decimals,
                )
                unknown_assets.add(unknown_asset)

        return asset_price

    @staticmethod
    def _get_unknown_asset_price_graph(
            unknown_assets: Set[UnknownEthereumToken],
            graph_query: Callable,
    ) -> AssetPrice:
        """Get today's tokens prices via the Uniswap subgraph

        Uniswap provides a token price every day at 00:00:00 UTC
        """
        asset_price: AssetPrice = {}

        unknown_assets_addresses = (
            [asset.ethereum_address for asset in unknown_assets]
        )
        unknown_assets_addresses_lower = (
            [address.lower() for address in unknown_assets_addresses]
        )

        querystr = format_query_indentation(TOKEN_DAY_DATAS_QUERY.format())
        today_epoch = int(
            datetime.combine(datetime.utcnow().date(), time.min).timestamp(),
        )
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$token_ids': '[String!]',
            '$datetime': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'token_ids': unknown_assets_addresses_lower,
            'datetime': today_epoch,
        }
        while True:
            result = graph_query(
                querystr=querystr,
                param_types=param_types,
                param_values=param_values,
            )
            result_data = result['tokenDayDatas']

            for tdd in result_data:
                token_address = to_checksum_address(tdd['token']['id'])
                asset_price[token_address] = Price(FVal(tdd['priceUSD']))

            # Check whether an extra request is needed
            if len(result_data) < GRAPH_QUERY_LIMIT:
                break

            # Update pagination step
            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return asset_price

    @staticmethod
    def _update_assets_prices_in_address_balances(
            address_balances: AddressBalances,
            known_asset_price: AssetPrice,
            unknown_asset_price: AssetPrice,
    ) -> None:
        """Update the pools underlying assets prices in USD (prices obtained
        via Inquirer and the Uniswap subgraph)
        """
        for lps in address_balances.values():
            for lp in lps:
                # Try to get price from either known or unknown asset price.
                # Otherwise keep existing price (zero)
                total_user_balance = FVal(0)
                for asset in lp.assets:
                    asset_ethereum_address = asset.asset.ethereum_address
                    asset_usd_price = known_asset_price.get(
                        asset_ethereum_address,
                        unknown_asset_price.get(asset_ethereum_address, Price(ZERO)),
                    )
                    # Update <LiquidityPoolAsset> if asset USD price exists
                    if asset_usd_price != Price(ZERO):
                        asset.usd_price = asset_usd_price
                        asset.user_balance.usd_value = FVal(
                            asset.user_balance.amount * asset_usd_price,
                        )

                    total_user_balance += asset.user_balance.usd_value

                # Update <LiquidityPool> total balance in USD
                lp.user_balance.usd_value = total_user_balance

    def get_balances(
        self,
        addresses: List[ChecksumEthAddress],
        is_graph_query: bool,
    ) -> AddressBalances:
        """Get the addresses' balances in the Uniswap protocol

        Premium users can request balances either via the Uniswap subgraph or
        Zerion SDK.
        """
        is_graph_mode = self.graph and self.premium and is_graph_query

        if is_graph_mode:
            protocol_balance = self._get_balances_graph(
                addresses=addresses,
                graph_query=self.graph.query,  # type: ignore
            )
        else:
            protocol_balance = self._get_balances_chain(addresses)

        known_assets = protocol_balance.known_assets
        unknown_assets = protocol_balance.unknown_assets

        known_asset_price = self._get_known_asset_price(
            known_assets=known_assets,
            unknown_assets=unknown_assets,
            price_query=Inquirer().find_usd_price,
        )

        unknown_asset_price: AssetPrice = {}
        if is_graph_mode:
            unknown_asset_price = self._get_unknown_asset_price_graph(
                unknown_assets=unknown_assets,
                graph_query=self.graph.query,  # type: ignore
            )

        self._update_assets_prices_in_address_balances(
            address_balances=protocol_balance.address_balances,
            known_asset_price=known_asset_price,
            unknown_asset_price=unknown_asset_price,
        )

        return protocol_balance.address_balances

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
