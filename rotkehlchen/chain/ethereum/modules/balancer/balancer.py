import datetime
import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from eth_utils import to_checksum_address
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.assets.utils import get_ethereum_token
from rotkehlchen.chain.ethereum.graph import GRAPH_QUERY_LIMIT, Graph, format_query_indentation
from rotkehlchen.chain.ethereum.modules.uniswap.graph import TOKEN_DAY_DATAS_QUERY
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_price
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .graph import POOLSHARES_QUERY, TOKENPRICES_QUERY
from .typing import (
    AddressBalances,
    BalancerPool,
    BalancerPoolToken,
    DDAddressBalances,
    ProtocolBalance,
    TokenPrices,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancer(EthereumModule):
    """Balancer integration module

    * Balancer subgraph:
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
        self.trades_lock = Semaphore()
        try:
            self.graph: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/balancer-labs/balancer',
            )
        except RemoteError as e:
            self.graph = None
            self.msg_aggregator.add_error(
                f"Could not initialize the Balancer subgraph due to {str(e)}. "
                f"All Balancer balances and historical queries are not functioning until this is fixed. "  # noqa: E501
                f"Probably will get fixed with time. If not report it to rotki's support channel",
            )
        try:
            self.graph_uniswap: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
            )
        except RemoteError as e:
            self.graph_uniswap = None
            self.msg_aggregator.add_error(
                f"Could not initialize the Uniswap subgraph due to {str(e)}. "
                f"All Balancer balances and historical queries won't be able to use a "
                f"secondary price oracle for requesting the USD price of the unsupported tokens. "
                f"Probably will get fixed with time. If not report it to rotki's support channel",
            )

    @staticmethod
    def _deserialize_pool_share(
            raw_pool_share: Dict[str, Any],
    ) -> Tuple[ChecksumEthAddress, BalancerPool]:
        """May raise DeserializationError"""
        try:
            user_address = raw_pool_share['userAddress']['id']
            user_amount = deserialize_asset_amount(raw_pool_share['balance'])
            raw_pool = raw_pool_share['poolId']
            total_amount = deserialize_asset_amount(raw_pool['totalShares'])
            address = raw_pool['id']
            raw_tokens = raw_pool['tokens']
            total_weight = deserialize_asset_amount(raw_pool['totalWeight'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        try:
            user_address = to_checksum_address(user_address)
            address = to_checksum_address(address)
        except ValueError as e:
            raise DeserializationError(
                f'Invalid ethereum address: {address} in pool.',  # noqa: E501
            ) from e

        pool_tokens = []
        for raw_token in raw_tokens:
            try:
                token_address = raw_token['address']
                token_symbol = raw_token['symbol']
                token_name = raw_token['name']
                token_decimals = raw_token['decimals']
                token_total_amount = deserialize_asset_amount(raw_token['balance'])
                token_weight = deserialize_asset_amount(raw_token['denormWeight'])
            except KeyError as e:
                raise DeserializationError(f'Missing key: {str(e)}.') from e

            try:
                token_address = to_checksum_address(token_address)
            except ValueError as e:
                raise DeserializationError(
                    f'Invalid ethereum address: {token_address} in pool token: {token_symbol}.',  # noqa: E501
                ) from e

            token = get_ethereum_token(
                symbol=token_symbol,
                ethereum_address=token_address,
                name=token_name,
                decimals=token_decimals,
            )
            token_user_amount = user_amount / total_amount * token_total_amount
            weight = token_weight * 100 / total_weight
            pool_token = BalancerPoolToken(
                token=token,
                total_amount=token_total_amount,
                user_balance=Balance(amount=token_user_amount),
                weight=weight,
            )
            pool_tokens.append(pool_token)

        pool = BalancerPool(
            address=address,
            tokens=pool_tokens,
            total_amount=total_amount,
            user_balance=Balance(amount=user_amount),
        )
        return user_address, pool

    @staticmethod
    def _deserialize_token_price(
            raw_token_price: Dict[str, Any],
    ) -> Tuple[ChecksumEthAddress, Price]:
        """May raise DeserializationError"""
        try:
            token_address = raw_token_price['id']
            usd_price = deserialize_price(raw_token_price['price'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        try:
            token_address = to_checksum_address(token_address)
        except ValueError as e:
            raise DeserializationError(
                f'Invalid ethereum address: {token_address} in token price.',
            ) from e

        return token_address, usd_price

    @staticmethod
    def _deserialize_token_day_data(
            raw_token_day_data: Dict[str, Any],
    ) -> Tuple[ChecksumEthAddress, Price]:
        """May raise DeserializationError"""
        try:
            token_address = raw_token_day_data['token']['id']
            usd_price = deserialize_price(raw_token_day_data['priceUSD'])
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        try:
            token_address = to_checksum_address(token_address)
        except ValueError as e:
            raise DeserializationError(
                f'Invalid ethereum address: {token_address} in token day data.',
            ) from e

        return token_address, usd_price

    def _get_balances_graph(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> ProtocolBalance:
        """Get the balances in the pools querying the Balancer subgraph

        May raise RemoteError
        """
        known_tokens: Set[EthereumToken] = set()
        unknown_tokens: Set[UnknownEthereumToken] = set()
        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(POOLSHARES_QUERY.format())
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[ID!]',
            '$balance': 'BigDecimal!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'addresses': addresses_lower,
            'balance': '0',
        }
        address_balances: DDAddressBalances = defaultdict(list)
        while True:
            try:
                result = self.graph.query(  # type: ignore # caller already checks
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f"Failed to request the Balancer subgraph due to {str(e)}. "
                    f"All Balancer balances and historical queries are not functioning until this is fixed. "  # noqa: E501
                    f"Probably will get fixed with time. If not report it to rotki's support channel",  # noqa: E501
                )
                raise

            try:
                raw_pool_shares = result['poolShares']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer balances',
                    error='Missing key: poolShares',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer balances') from e

            for raw_pool_share in raw_pool_shares:
                try:
                    address, balancer_pool = self._deserialize_pool_share(raw_pool_share)
                    for pool_token in balancer_pool.tokens:
                        if isinstance(pool_token.token, EthereumToken):
                            known_tokens.add(pool_token.token)
                        elif isinstance(pool_token.token, UnknownEthereumToken):
                            unknown_tokens.add(pool_token.token)
                        else:
                            raise AssertionError(f'Unexpected type: {type(pool_token.token)}')
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer pool balance',
                        error=str(e),
                        raw_pool_share=raw_pool_share,
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer balances') from e

                address_balances[address].append(balancer_pool)

            if len(raw_pool_shares) < GRAPH_QUERY_LIMIT:
                break

            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        protocol_balance = ProtocolBalance(
            address_balances=dict(address_balances),
            known_tokens=known_tokens,
            unknown_tokens=unknown_tokens,
        )
        return protocol_balance

    def _get_known_token_prices(self, known_tokens: Set[EthereumToken]) -> TokenPrices:
        """Get the USD price of the known tokens"""
        token_prices: TokenPrices = {}
        for token in known_tokens:
            usd_price = Inquirer().find_usd_price(token)
            if usd_price == Price(ZERO):
                self.msg_aggregator.add_error(
                    f"Failed to request the USD price of {token.identifier}. "
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
                continue

            token_prices[token.ethereum_address] = usd_price
        return token_prices

    def _get_unknown_token_prices_graph(
            self,
            unknown_tokens: Set[UnknownEthereumToken],
    ) -> TokenPrices:
        """Attempt to get the last token price using multiple price oracles,
        first Balancer and then Uniswap (if necessary).

        May raise RemoteError
        """
        unknown_token_addresses = {token.ethereum_address for token in unknown_tokens}
        token_prices_bal = self._get_unknown_token_prices_balancer_graph(unknown_token_addresses)
        token_prices = dict(token_prices_bal)
        still_unknown_token_addresses = unknown_token_addresses - set(token_prices_bal.keys())
        if self.graph_uniswap:
            # Requesting the missing UnknownEthereumToken prices to Uniswap is
            # a nice to have alternative to the main oracle (Balancer). Therefore
            # in case of failing to request it we just continue.
            try:
                token_prices_uni = self._get_unknown_token_prices_uniswap_graph(still_unknown_token_addresses)  # noqa: E501
            except RemoteError:
                # This error hiding is exclusive of the Balancer module. The Uniswap
                # module also calls tokenDayDatas and processes the results in the
                # same way, so in case of an error we should know.
                token_prices_uni = {}

            token_prices = {**token_prices, **token_prices_uni}

        for unknown_token in unknown_tokens:
            if unknown_token.ethereum_address not in token_prices:
                self.msg_aggregator.add_error(
                    f"Failed to request the USD price of {unknown_token.identifier}. "
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
        return token_prices

    def _get_unknown_token_prices_balancer_graph(
            self,
            unknown_token_addresses: Set[ChecksumEthAddress],
    ) -> TokenPrices:
        """Get the last token price via the balancer subgraph

        May raise RemoteError
        """
        unknown_token_addresses_lower = [address.lower() for address in unknown_token_addresses]
        querystr = format_query_indentation(TOKENPRICES_QUERY.format())
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$token_ids': '[ID!]',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'token_ids': unknown_token_addresses_lower,
        }
        token_prices: TokenPrices = {}
        while True:
            try:
                result = self.graph.query(  # type: ignore # caller already checks
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f"Failed to request the Balancer subgraph due to {str(e)}. "
                    f"All Balancer balances and historical queries are not functioning until this is fixed. "  # noqa: E501
                    f"Probably will get fixed with time. If not report it to rotki's support channel",  # noqa: E501
                )
                raise

            try:
                raw_token_prices = result['tokenPrices']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer unknown token prices',
                    error='Missing key: tokenPrices',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer balances') from e

            for raw_token_price in raw_token_prices:
                try:
                    token_address, usd_price = self._deserialize_token_price(raw_token_price)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer unknown token price',
                        error=str(e),
                        raw_token_price=raw_token_price,
                        param_values=param_values,
                    )
                    continue

                token_prices[token_address] = usd_price

            if len(raw_token_prices) < GRAPH_QUERY_LIMIT:
                break

            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return token_prices

    def _get_unknown_token_prices_uniswap_graph(
            self,
            unknown_token_addresses: Set[ChecksumEthAddress],
    ) -> TokenPrices:
        """Get today's token price via the uniswap subgraph

        May raise RemoteError
        """
        unknown_token_addresses_lower = [address.lower() for address in unknown_token_addresses]
        querystr = format_query_indentation(TOKEN_DAY_DATAS_QUERY.format())
        today_epoch = int(
            datetime.datetime.combine(
                datetime.datetime.fromtimestamp(time.time()),
                datetime.time.min,
            ).timestamp(),
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
            'token_ids': unknown_token_addresses_lower,
            'datetime': today_epoch,
        }
        token_prices: TokenPrices = {}
        while True:
            try:
                result = self.graph_uniswap.query(  # type: ignore # caller already checks
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f"Failed to request the Uniswap subgraph due to {str(e)}. "
                    f"All Balancer balances won't be able to use Uniswap as a secondary "
                    f"price oracle for requesting the USD price of the unsupported tokens. "
                    f"Probably will get fixed with time. If not report it to rotki's support channel.",  # noqa: E501
                )
                raise

            try:
                raw_token_day_datas = result['tokenDayDatas']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer unknown token day datas',
                    error='Missing key: tokenDayDatas',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer balances') from e

            for raw_token_day_data in raw_token_day_datas:
                try:
                    token_address, usd_price = self._deserialize_token_day_data(raw_token_day_data)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer unknown token day data',
                        error=str(e),
                        raw_token_day_data=raw_token_day_data,
                        param_values=param_values,
                    )
                    continue

                token_prices[token_address] = usd_price

            if len(raw_token_day_datas) < GRAPH_QUERY_LIMIT:
                break

            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return token_prices

    @staticmethod
    def _update_tokens_prices_in_address_balances(
            address_balances: AddressBalances,
            known_token_prices: TokenPrices,
            unknown_token_prices: TokenPrices,
    ) -> None:
        """Update the prices (in USD) of the underlying pool tokens"""
        for balancer_pools in address_balances.values():
            for balancer_pool in balancer_pools:
                total_usd_value = ZERO
                for pool_token in balancer_pool.tokens:
                    token_ethereum_address = pool_token.token.ethereum_address
                    usd_price = known_token_prices.get(
                        token_ethereum_address,
                        unknown_token_prices.get(token_ethereum_address, Price(ZERO)),
                    )
                    if usd_price != Price(ZERO):
                        pool_token.usd_price = usd_price
                        pool_token.user_balance.usd_value = FVal(
                            pool_token.user_balance.amount * usd_price,
                        )
                    total_usd_value += pool_token.user_balance.usd_value
                balancer_pool.user_balance.usd_value = total_usd_value

    def get_balances(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> AddressBalances:
        """Get the balances of the addresses

        May raise RemoteError
        """
        is_graph_mode = self.graph is not None and self.premium
        if not is_graph_mode:
            raise NotImplementedError(
                'Getting Balancer balances for non premium user is not implemented',
            )

        protocol_balance = self._get_balances_graph(addresses)
        known_tokens = protocol_balance.known_tokens
        unknown_tokens = protocol_balance.unknown_tokens
        known_token_prices = self._get_known_token_prices(known_tokens)
        unknown_token_prices = self._get_unknown_token_prices_graph(unknown_tokens)
        self._update_tokens_prices_in_address_balances(
            address_balances=protocol_balance.address_balances,
            known_token_prices=known_token_prices,
            unknown_token_prices=unknown_token_prices,
        )
        return protocol_balance.address_balances

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
