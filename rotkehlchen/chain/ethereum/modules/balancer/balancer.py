import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from gevent.lock import Semaphore

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.graph import (
    GRAPH_QUERY_LIMIT,
    SUBGRAPH_REMOTE_ERROR_MSG,
    Graph,
    format_query_indentation,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.api import APIKeyNotConfigured
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .graph import POOLSHARES_QUERY, TOKENPRICES_QUERY
from .types import AddressToPoolBalances, DDAddressToPoolBalances, ProtocolBalance, TokenToPrices
from .utils import deserialize_pool_share, deserialize_token_price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancer(EthereumModule):
    """Balancer integration module"""
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.trades_lock = Semaphore()
        try:
            # If both fail, let's take the safest approach and consider the module unusable
            self.graph = Graph(
                subgraph_id='93yusydMYauh7cfe9jEfoGABmwnX4GffHd7in8KJi1XB',
                database=self.database,
                label='balancer',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                SUBGRAPH_REMOTE_ERROR_MSG.format(protocol='Balancer', error_msg=str(e)),
            )
            raise ModuleInitializationFailure('subgraph remote error') from e

    def _get_known_token_to_prices(self, known_tokens: set[EvmToken]) -> TokenToPrices:
        """Get a mapping of known token addresses to USD price"""
        token_to_prices: TokenToPrices = {}
        for token in known_tokens:
            if (usd_price := Inquirer.find_usd_price(token)) == ZERO_PRICE:
                self.msg_aggregator.add_error(
                    f'Failed to request the USD price of {token.identifier}. '
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
                continue

            token_to_prices[token.evm_address] = usd_price
        return token_to_prices

    def _get_protocol_balance_graph(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> ProtocolBalance:
        """Get a mapping of addresses to protocol balance.

        May raise RemoteError
        """
        known_tokens: set[EvmToken] = set()
        unknown_tokens: set[EvmToken] = set()
        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(POOLSHARES_QUERY.format())
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[ID!]',
            '$balance': 'BigDecimal!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'addresses': addresses_lower,
            'balance': '0',
        }
        address_to_pool_balances: DDAddressToPoolBalances = defaultdict(list)
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(protocol='Balancer', error_msg=str(e)),
                )
                raise
            except APIKeyNotConfigured as e:
                log.warning(f'Api key for balancer not configured when querying balancer balances. Skipping. {e}')  # noqa: E501
                break

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
                    address, balancer_pool = deserialize_pool_share(self.database, raw_pool_share)
                    for pool_token in balancer_pool.pool_token.underlying_tokens:
                        token = EvmToken(ethaddress_to_identifier(pool_token.address))  # should not raise  # noqa: E501
                        if token.has_oracle():
                            known_tokens.add(token)
                        else:
                            unknown_tokens.add(token)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer pool balance',
                        error=str(e),
                        raw_pool_share=raw_pool_share,
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer balances') from e

                address_to_pool_balances[address].append(balancer_pool)

            if len(raw_pool_shares) < GRAPH_QUERY_LIMIT:
                break

            query_offset += GRAPH_QUERY_LIMIT
            param_values = {
                **param_values,
                'offset': query_offset,
            }

        protocol_balance = ProtocolBalance(
            address_to_pool_balances=dict(address_to_pool_balances),
            known_tokens=known_tokens,
            unknown_tokens=unknown_tokens,
        )
        return protocol_balance

    def _get_unknown_token_to_prices_balancer_graph(
            self,
            unknown_token_addresses: set[ChecksumEvmAddress],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price via Balancer

        May raise RemoteError
        """
        unknown_token_addresses_lower = [address.lower() for address in unknown_token_addresses]
        querystr = format_query_indentation(TOKENPRICES_QUERY.format())
        query_offset = 0
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$token_ids': '[ID!]',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': query_offset,
            'token_ids': unknown_token_addresses_lower,
        }
        token_to_prices: TokenToPrices = {}
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    SUBGRAPH_REMOTE_ERROR_MSG.format(protocol='Balancer', error_msg=str(e)),
                )
                raise
            except APIKeyNotConfigured as e:
                log.warning(f'Api key for balancer not configured when querying balancer prices. Skipping. {e}')  # noqa: E501
                break

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
                    token_address, usd_price = deserialize_token_price(raw_token_price)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer unknown token price',
                        error=str(e),
                        raw_token_price=raw_token_price,
                        param_values=param_values,
                    )
                    continue

                token_to_prices[token_address] = usd_price

            if len(raw_token_prices) < GRAPH_QUERY_LIMIT:
                break

            query_offset += GRAPH_QUERY_LIMIT
            param_values = {
                **param_values,
                'offset': query_offset,
            }

        return token_to_prices

    def _get_unknown_token_to_prices_graph(
            self,
            unknown_tokens: set[EvmToken],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price

        Attempts first to get the price via Balancer, otherwise via Uniswap

        May raise RemoteError
        """
        unknown_token_addresses = {token.evm_address for token in unknown_tokens}
        token_to_prices_bal = self._get_unknown_token_to_prices_balancer_graph(unknown_token_addresses)  # noqa: E501
        token_to_prices = dict(token_to_prices_bal)
        for unknown_token in unknown_tokens:
            if unknown_token.evm_address not in token_to_prices:
                self.msg_aggregator.add_error(
                    f'Failed to request the USD price of {unknown_token.identifier}. '
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
        return token_to_prices

    @staticmethod
    def _update_tokens_prices_in_address_to_pool_balances(
            address_to_pool_balances: AddressToPoolBalances,
            known_token_to_prices: TokenToPrices,
            unknown_token_to_prices: TokenToPrices,
    ) -> None:
        """Update the prices (in USD) of the underlying pool tokens"""
        for balancer_pool_balances in address_to_pool_balances.values():
            for pool_balance in balancer_pool_balances:
                total_usd_value = ZERO
                for pool_token_balance in pool_balance.underlying_tokens_balance:
                    token_ethereum_address = pool_token_balance.token.evm_address
                    usd_price = known_token_to_prices.get(
                        token_ethereum_address,
                        unknown_token_to_prices.get(token_ethereum_address, ZERO_PRICE),
                    )
                    if usd_price != ZERO_PRICE:
                        pool_token_balance.usd_price = usd_price
                        pool_token_balance.user_balance.usd_value = FVal(
                            pool_token_balance.user_balance.amount * usd_price,
                        )
                    total_usd_value += pool_token_balance.user_balance.usd_value
                pool_balance.user_balance.usd_value = total_usd_value

    def get_balances(
            self,
            addresses: list[ChecksumEvmAddress],
    ) -> AddressToPoolBalances:
        """Get the balances of the given addresses in any Balancer pool

        May raise RemoteError
        """
        protocol_balance = self._get_protocol_balance_graph(addresses)
        known_tokens = protocol_balance.known_tokens
        unknown_tokens = protocol_balance.unknown_tokens
        known_token_to_prices = self._get_known_token_to_prices(known_tokens)
        unknown_token_to_prices = self._get_unknown_token_to_prices_graph(unknown_tokens)
        self._update_tokens_prices_in_address_to_pool_balances(
            address_to_pool_balances=protocol_balance.address_to_pool_balances,
            known_token_to_prices=known_token_to_prices,
            unknown_token_to_prices=unknown_token_to_prices,
        )
        return protocol_balance.address_to_pool_balances

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        ...

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        ...

    def deactivate(self) -> None:
        ...
