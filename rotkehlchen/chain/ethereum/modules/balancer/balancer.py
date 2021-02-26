import datetime
import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING, List, Optional, Set

from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.chain.ethereum.graph import (
    GRAPH_QUERY_LIMIT,
    GRAPH_QUERY_SKIP_LIMIT,
    Graph,
    format_query_indentation,
)
from rotkehlchen.chain.ethereum.modules.uniswap.graph import TOKEN_DAY_DATAS_QUERY
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError, ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Location, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .graph import POOLSHARES_QUERY, SWAPS_QUERY, TOKENPRICES_QUERY
from .typing import (
    BALANCER_TRADES_PREFIX,
    AddressToBalances,
    AddressToSwaps,
    AddressToTrades,
    DDAddressToBalances,
    DDAddressToSwaps,
    ProtocolBalance,
    TokenToPrices,
)
from .utils import (
    SUBGRAPH_REMOTE_ERROR_MSG,
    UNISWAP_REMOTE_ERROR_MSG,
    deserialize_pool_share,
    deserialize_swap,
    deserialize_token_day_data,
    deserialize_token_price,
    get_trades_from_tx_swaps,
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
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/balancer-labs/balancer',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('subgraph remote error') from e

        try:
            self.graph_uniswap: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
            )
        except RemoteError as e:
            self.graph_uniswap = None
            self.msg_aggregator.add_error(UNISWAP_REMOTE_ERROR_MSG.format(error_msg=str(e)))

    def _fetch_trades_from_db(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> AddressToTrades:
        """Fetch all DB Balancer swaps within the time range and format as trades"""
        db_address_to_trades: AddressToTrades = {}
        for address in addresses:
            db_swaps = self.database.get_amm_swaps(
                from_ts=from_timestamp,
                to_ts=to_timestamp,
                location=Location.BALANCER,
                address=address,
            )
            if db_swaps:
                db_trades = self._get_trades_from_swaps(db_swaps)
                db_address_to_trades[address] = db_trades

        return db_address_to_trades

    def _get_protocol_balance_graph(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> ProtocolBalance:
        """Get a mapping of addresses to protocol balance.

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
        address_to_balances: DDAddressToBalances = defaultdict(list)
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
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
                    address, balancer_pool = deserialize_pool_share(raw_pool_share)
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

                address_to_balances[address].append(balancer_pool)

            if len(raw_pool_shares) < GRAPH_QUERY_LIMIT:
                break

            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        protocol_balance = ProtocolBalance(
            address_to_balances=dict(address_to_balances),
            known_tokens=known_tokens,
            unknown_tokens=unknown_tokens,
        )
        return protocol_balance

    def _get_known_token_to_prices(self, known_tokens: Set[EthereumToken]) -> TokenToPrices:
        """Get a mapping of known token addresses to USD price"""
        token_to_prices: TokenToPrices = {}
        for token in known_tokens:
            usd_price = Inquirer().find_usd_price(token)
            if usd_price == Price(ZERO):
                self.msg_aggregator.add_error(
                    f"Failed to request the USD price of {token.identifier}. "
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
                continue

            token_to_prices[token.ethereum_address] = usd_price
        return token_to_prices

    def _get_address_to_trades(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            only_cache: bool,
    ) -> AddressToTrades:
        """Get a mapping of addresses to trades for the given time range

        Requests all the new swaps (since last used query range) of the existing
        addresses via subgraph.

        May raise RemoteError
        """
        address_to_swaps: AddressToSwaps = {}
        new_addresses: List[ChecksumEthAddress] = []
        existing_addresses: List[ChecksumEthAddress] = []
        min_end_ts: Timestamp = to_timestamp

        if only_cache:
            return self._fetch_trades_from_db(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
            )

        # Get addresses' last used query range for Balancer trades
        for address in addresses:
            entry_name = f'{BALANCER_TRADES_PREFIX}_{address}'
            trades_range = self.database.get_used_query_range(name=entry_name)

            if not trades_range:
                new_addresses.append(address)
            else:
                existing_addresses.append(address)
                min_end_ts = min(min_end_ts, trades_range[1])

        # Request new addresses' trades
        if new_addresses:
            start_ts = Timestamp(0)
            new_address_to_swaps = self._get_address_to_swaps_graph(
                addresses=new_addresses,
                start_ts=start_ts,
                end_ts=to_timestamp,
            )
            address_to_swaps.update(new_address_to_swaps)
            self._update_used_query_range(
                addresses=new_addresses,
                prefix='balancer_trades',
                start_ts=start_ts,
                end_ts=to_timestamp,
            )

        # Request existing DB addresses' trades
        if existing_addresses and to_timestamp > min_end_ts:
            address_new_swaps = self._get_address_to_swaps_graph(
                addresses=existing_addresses,
                start_ts=min_end_ts,
                end_ts=to_timestamp,
            )
            address_to_swaps.update(address_new_swaps)
            self._update_used_query_range(
                addresses=existing_addresses,
                prefix='balancer_trades',
                start_ts=min_end_ts,
                end_ts=to_timestamp,
            )

        # Insert all unique swaps to the DB
        if address_to_swaps:
            all_swaps = {swap for a_swaps in address_to_swaps.values() for swap in a_swaps}
            self.database.add_amm_swaps(list(all_swaps))

        return self._fetch_trades_from_db(
            addresses=addresses,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

    def _get_address_to_swaps_graph(
            self,
            addresses: List[ChecksumEthAddress],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> AddressToSwaps:
        """Get a mapping of addresses to swaps for the given time range

        May raise RemoteError
        """
        addresses_lower = [address.lower() for address in addresses]
        querystr = format_query_indentation(SWAPS_QUERY.format())
        param_types = {
            '$limit': 'Int!',
            '$offset': 'Int!',
            '$addresses': '[ID!]',
            '$start_ts': 'Int!',
            '$end_ts': 'Int!',
        }
        param_values = {
            'limit': GRAPH_QUERY_LIMIT,
            'offset': 0,
            'addresses': addresses_lower,
            'start_ts': start_ts,
            'end_ts': end_ts,
        }
        address_to_swaps: DDAddressToSwaps = defaultdict(list)
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
                raise

            try:
                raw_swaps = result['swaps']
            except KeyError as e:
                log.error(
                    'Failed to deserialize balancer swaps',
                    error='Missing key: swaps',
                    result=result,
                    param_values=param_values,
                )
                raise RemoteError('Failed to deserialize balancer trades') from e

            for raw_swap in raw_swaps:
                try:
                    amm_swap = deserialize_swap(raw_swap)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer swap',
                        error=str(e),
                        raw_swap=raw_swap,
                        start_ts=start_ts,  # initial value
                        end_ts=end_ts,  # initial value
                        param_values=param_values,
                    )
                    raise RemoteError('Failed to deserialize balancer trades') from e

                address_to_swaps[amm_swap.address].append(amm_swap)

            if len(raw_swaps) < GRAPH_QUERY_LIMIT:
                break

            if param_values['offset'] == GRAPH_QUERY_SKIP_LIMIT:
                query_start_ts = amm_swap.timestamp
                query_offset = 0
            else:
                query_start_ts = param_values['start_ts']  # type: ignore
                query_offset = param_values['offset'] + GRAPH_QUERY_LIMIT  # type: ignore

            param_values = {
                **param_values,
                'start_ts': query_start_ts,
                'offset': query_offset,
            }

        return address_to_swaps

    @staticmethod
    def _get_trades_from_swaps(swaps: List[AMMSwap]) -> List[AMMTrade]:
        assert len(swaps) != 0, "Swaps can't be an empty list"

        swaps.sort(key=lambda swap: (swap.timestamp, -swap.log_index), reverse=True)
        current_swaps: List[AMMSwap] = []
        trades: List[AMMTrade] = []
        last_tx_hash = swaps[0].tx_hash
        for swap in swaps:
            if swap.tx_hash != last_tx_hash:
                trades.extend(get_trades_from_tx_swaps(current_swaps))
                last_tx_hash = swap.tx_hash
                current_swaps = []

            current_swaps.append(swap)

        if len(current_swaps) != 0:
            trades.extend(get_trades_from_tx_swaps(current_swaps))

        return trades

    def _get_unknown_token_to_prices_graph(
            self,
            unknown_tokens: Set[UnknownEthereumToken],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price

        Attempts first to get the price via Balancer, otherwise via Uniswap

        May raise RemoteError
        """
        unknown_token_addresses = {token.ethereum_address for token in unknown_tokens}
        token_to_prices_bal = self._get_unknown_token_to_prices_balancer_graph(unknown_token_addresses)  # noqa: E501
        token_to_prices = dict(token_to_prices_bal)
        still_unknown_token_addresses = unknown_token_addresses - set(token_to_prices_bal.keys())
        if self.graph_uniswap is not None:
            # Requesting the missing UnknownEthereumToken prices from Uniswap is
            # a nice to have alternative to the main oracle (Balancer). Therefore
            # in case of failing to request, it will just continue.
            try:
                token_to_prices_uni = self._get_unknown_token_to_prices_uniswap_graph(still_unknown_token_addresses)  # noqa: E501
            except RemoteError:
                # This error hiding is exclusive of the Balancer module. The Uniswap
                # module also calls tokenDayDatas and processes the results in the
                # same way, so in case of an error we should know.
                token_to_prices_uni = {}

            token_to_prices = {**token_to_prices, **token_to_prices_uni}

        for unknown_token in unknown_tokens:
            if unknown_token.ethereum_address not in token_to_prices:
                self.msg_aggregator.add_error(
                    f"Failed to request the USD price of {unknown_token.identifier}. "
                    f"Balances of the balancer pools that have this token won't be accurate.",
                )
        return token_to_prices

    def _get_unknown_token_to_prices_balancer_graph(
            self,
            unknown_token_addresses: Set[ChecksumEthAddress],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price via Balancer

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
        token_to_prices: TokenToPrices = {}
        while True:
            try:
                result = self.graph.query(
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
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

            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return token_to_prices

    def _get_unknown_token_to_prices_uniswap_graph(
            self,
            unknown_token_addresses: Set[ChecksumEthAddress],
    ) -> TokenToPrices:
        """Get a mapping of unknown token addresses to USD price via Uniswap

        May raise RemoteError
        """
        unknown_token_addresses_lower = [address.lower() for address in unknown_token_addresses]
        querystr = format_query_indentation(TOKEN_DAY_DATAS_QUERY.format())
        midnight_epoch = int(
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
            'datetime': midnight_epoch,
        }
        token_to_prices: TokenToPrices = {}
        while True:
            try:
                result = self.graph_uniswap.query(  # type: ignore # caller already checks
                    querystr=querystr,
                    param_types=param_types,
                    param_values=param_values,
                )
            except RemoteError as e:
                self.msg_aggregator.add_error(UNISWAP_REMOTE_ERROR_MSG.format(error_msg=str(e)))
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
                    token_address, usd_price = deserialize_token_day_data(raw_token_day_data)
                except DeserializationError as e:
                    log.error(
                        'Failed to deserialize a balancer unknown token day data',
                        error=str(e),
                        raw_token_day_data=raw_token_day_data,
                        param_values=param_values,
                    )
                    continue

                token_to_prices[token_address] = usd_price

            if len(raw_token_day_datas) < GRAPH_QUERY_LIMIT:
                break

            param_values = {
                **param_values,
                'offset': param_values['offset'] + GRAPH_QUERY_LIMIT,  # type: ignore
            }

        return token_to_prices

    def _update_used_query_range(
            self,
            addresses: List[ChecksumEthAddress],
            prefix: Literal['balancer_trades'],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        for address in addresses:
            entry_name = f'{prefix}_{address}'
            self.database.update_used_query_range(
                name=entry_name,
                start_ts=start_ts,
                end_ts=end_ts,
            )

    @staticmethod
    def _update_tokens_prices_in_address_to_balances(
            address_to_balances: AddressToBalances,
            known_token_to_prices: TokenToPrices,
            unknown_token_to_prices: TokenToPrices,
    ) -> None:
        """Update the prices (in USD) of the underlying pool tokens"""
        for balancer_pools in address_to_balances.values():
            for balancer_pool in balancer_pools:
                total_usd_value = ZERO
                for pool_token in balancer_pool.tokens:
                    token_ethereum_address = pool_token.token.ethereum_address
                    usd_price = known_token_to_prices.get(
                        token_ethereum_address,
                        unknown_token_to_prices.get(token_ethereum_address, Price(ZERO)),
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
    ) -> AddressToBalances:
        """Get the balances of the given addresses in any Balancer pool

        May raise RemoteError
        """
        protocol_balance = self._get_protocol_balance_graph(addresses)
        known_tokens = protocol_balance.known_tokens
        unknown_tokens = protocol_balance.unknown_tokens
        known_token_to_prices = self._get_known_token_to_prices(known_tokens)
        unknown_token_to_prices = self._get_unknown_token_to_prices_graph(unknown_tokens)
        self._update_tokens_prices_in_address_to_balances(
            address_to_balances=protocol_balance.address_to_balances,
            known_token_to_prices=known_token_to_prices,
            unknown_token_to_prices=unknown_token_to_prices,
        )
        return protocol_balance.address_to_balances

    def get_trades(
            self,
            addresses: List[ChecksumEthAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            only_cache: bool,
    ) -> List[AMMTrade]:
        with self.trades_lock:
            all_trades = []
            address_to_trades = self._get_address_to_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=only_cache,
            )
            for _, trades in address_to_trades.items():
                all_trades.extend(trades)

            return all_trades

    def get_trades_history(
        self,
        addresses: List[ChecksumEthAddress],
        reset_db_data: bool,
        from_timestamp: Timestamp,
        to_timestamp: Timestamp,
    ) -> AddressToTrades:
        """Get the trades history of the given addresses

        May raise RemoteError
        """
        with self.trades_lock:
            if reset_db_data is True:
                self.database.delete_balancer_trades_data()

            address_to_trades = self._get_address_to_trades(
                addresses=addresses,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                only_cache=False,
            )

        return address_to_trades

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_balancer_trades_data()
