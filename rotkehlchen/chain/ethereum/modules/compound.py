import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union

from typing_extensions import Literal

from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    BalanceType,
    DefiEvent,
    DefiEventType,
)
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.utils import symbol_to_asset_or_token, symbol_to_ethereum_token
from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
from rotkehlchen.chain.ethereum.graph import Graph, get_common_params
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.assets import A_COMP, A_ETH
from rotkehlchen.constants.ethereum import CTOKEN_ABI, ERC20TOKEN_ABI, EthereumConstants
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import BlockchainQueryError, RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hexstr_to_int, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

ADDRESS_TO_ASSETS = Dict[ChecksumEthAddress, Dict[Asset, Balance]]
BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365
ETH_MANTISSA = 10**18

COMPTROLLER_PROXY = EthereumConstants().contract('COMPTROLLER_PROXY')
COMP_DEPLOYED_BLOCK = 9601359

LEND_EVENTS_QUERY_PREFIX = """{graph_event_name}
(where: {{blockTime_lte: $end_ts, blockTime_gte: $start_ts, {addr_position}: $address}}) {{
    id
    amount
    to
    from
    blockNumber
    blockTime
    cTokenSymbol
    underlyingAmount
}}}}"""


BORROW_EVENTS_QUERY_PREFIX = """{graph_event_name}
 (where: {{blockTime_lte: $end_ts, blockTime_gte: $start_ts, borrower: $address}}) {{
    id
    amount
    borrower
    blockNumber
    blockTime
    underlyingSymbol
    {payer_or_empty}
}}}}"""


log = logging.getLogger(__name__)


class CompoundBalance(NamedTuple):
    balance_type: BalanceType
    balance: Balance
    apy: Optional[FVal]

    def serialize(self) -> Dict[str, Union[Optional[str], Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2) if self.apy else None,
        }


class CompoundEvent(NamedTuple):
    event_type: Literal['mint', 'redeem', 'borrow', 'repay', 'liquidation', 'comp']
    address: ChecksumEthAddress
    block_number: int
    timestamp: Timestamp
    asset: Asset
    value: Balance
    to_asset: Optional[Asset]
    to_value: Optional[Balance]
    realized_pnl: Optional[Balance]
    tx_hash: str
    log_index: int  # only used to identify uniqueness

    def serialize(self) -> Dict[str, Any]:
        serialized = self._asdict()  # pylint: disable=no-member
        del serialized['log_index']
        return serialized

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return f'Compound {self.event_type} event'


def _get_txhash_and_logidx(identifier: str) -> Optional[Tuple[str, int]]:
    result = identifier.split('-')
    if len(result) != 2:
        return None

    if len(result[0]) == 0 or len(result[1]) == 0:
        return None

    try:
        log_index = int(result[1])
    except ValueError:
        return None

    return result[0], log_index


def _compound_symbol_to_token(symbol: str, timestamp: Timestamp) -> EthereumToken:
    """
    Turns a compound symbol to an ethereum token.

    May raise UnknownAsset
    """
    if symbol == 'cWBTC':
        if timestamp >= Timestamp(1615751087):
            return EthereumToken('0xccF4429DB6322D5C611ee964527D42E5d685DD6a')
        # else
        return EthereumToken('0xC11b1268C1A384e55C48c2391d8d480264A3A7F4')
    # else
    return symbol_to_ethereum_token(symbol)


class Compound(EthereumModule):
    """Compound integration module

    https://compound.finance/docs#guides
    """

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ):
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        try:
            self.graph: Optional[Graph] = Graph(
                'https://api.thegraph.com/subgraphs/name/graphprotocol/compound-v2',
            )
        except RemoteError as e:
            self.graph = None
            self.msg_aggregator.add_error(
                f'Could not initialize the Compound subgraph due to {str(e)}. '
                f' All compound historical queries are not functioning until this is fixed. '
                f'Probably will get fixed with time. If not report it to rotkis support channel ',
            )

    def _get_apy(self, address: ChecksumEthAddress, supply: bool) -> Optional[FVal]:
        method_name = 'supplyRatePerBlock' if supply else 'borrowRatePerBlock'

        try:
            rate = self.ethereum.call_contract(
                contract_address=address,
                abi=CTOKEN_ABI,
                method_name=method_name,
            )
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Could not query cToken {address} for supply/borrow rate: {str(e)}')
            return None

        apy = ((FVal(rate) / ETH_MANTISSA * BLOCKS_PER_DAY) + 1) ** (DAYS_PER_YEAR - 1) - 1  # noqa: E501
        return apy

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, Dict[str, Dict[Asset, CompoundBalance]]]:
        compound_balances = {}
        now = ts_now()
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            rewards_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name not in ('Compound Governance', 'Compound'):
                    continue

                entry = balance_entry.base_balance
                if entry.token_address == '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE':
                    asset = A_ETH  # hacky way to specify ETH in compound
                else:
                    try:
                        asset = EthereumToken(entry.token_address)
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} with address '
                            f'{entry.token_address} in compound. Skipping',
                        )
                        continue

                unclaimed_comp_rewards = (
                    entry.token_address == A_COMP.ethereum_address and
                    balance_entry.protocol.name == 'Compound Governance'
                )
                if unclaimed_comp_rewards:
                    rewards_map[A_COMP] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=entry.balance,
                        apy=None,
                    )
                    continue

                if balance_entry.balance_type == 'Asset':
                    # Get the underlying balance
                    underlying_token_address = balance_entry.underlying_balances[0].token_address
                    try:
                        underlying_asset = EthereumToken(underlying_token_address)
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown token with address '
                            f'{underlying_token_address} in compound. Skipping',
                        )
                        continue

                    lending_map[underlying_asset] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=balance_entry.underlying_balances[0].balance,
                        apy=self._get_apy(entry.token_address, supply=True),
                    )
                else:  # 'Debt'
                    try:
                        ctoken = _compound_symbol_to_token(
                            symbol='c' + entry.token_symbol,
                            timestamp=now,
                        )
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} in '
                            f'compound while figuring out cToken. Skipping',
                        )
                        continue

                    borrowing_map[asset] = CompoundBalance(
                        balance_type=BalanceType.LIABILITY,
                        balance=entry.balance,
                        apy=self._get_apy(ctoken.ethereum_address, supply=False),
                    )

            if lending_map == {} and borrowing_map == {} and rewards_map == {}:
                # no balances for the account
                continue

            compound_balances[account] = {
                'rewards': rewards_map,
                'lending': lending_map,
                'borrowing': borrowing_map,
            }

        return compound_balances  # type: ignore

    def _get_borrow_events(
            self,
            event_type: Literal['borrow', 'repay'],
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types, param_values = get_common_params(from_ts, to_ts, address)
        if event_type == 'borrow':
            graph_event_name = 'borrowEvents'
            payer_or_empty = ''
        elif event_type == 'repay':
            graph_event_name = 'repayEvents'
            payer_or_empty = 'payer'

        result = self.graph.query(  # type: ignore
            querystr=BORROW_EVENTS_QUERY_PREFIX.format(
                graph_event_name=graph_event_name,
                payer_or_empty=payer_or_empty,
            ),
            param_types=param_types,
            param_values=param_values,
        )

        events = []
        for entry in result[graph_event_name]:
            underlying_symbol = entry['underlyingSymbol']
            try:
                underlying_asset = symbol_to_asset_or_token(underlying_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected token symbol {underlying_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            timestamp = entry['blockTime']
            usd_price = query_usd_price_zero_if_error(
                asset=underlying_asset,
                time=timestamp,
                location=f'compound {event_type}',
                msg_aggregator=self.msg_aggregator,
            )
            amount = FVal(entry['amount'])
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(
                    f'Found unprocessable borrow/repay id from the graph {entry["id"]}. Skipping',
                )
                continue

            events.append(CompoundEvent(
                event_type=event_type,
                address=address,
                block_number=entry['blockNumber'],
                timestamp=timestamp,
                asset=underlying_asset,
                value=Balance(amount=amount, usd_value=amount * usd_price),
                to_asset=None,
                to_value=None,
                realized_pnl=None,
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_liquidation_events(
            self,
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        """https://compound.finance/docs/ctokens#liquidate-borrow"""
        param_types, param_values = get_common_params(from_ts, to_ts, address)
        result = self.graph.query(  # type: ignore
            querystr="""liquidationEvents (where: {blockTime_lte: $end_ts, blockTime_gte: $start_ts, from: $address}) {
    id
    amount
    from
    blockNumber
    blockTime
    cTokenSymbol
    underlyingSymbol
    underlyingRepayAmount
}}""",
            param_types=param_types,
            param_values=param_values,
        )

        events = []
        for entry in result['liquidationEvents']:
            timestamp = entry['blockTime']
            ctoken_symbol = entry['cTokenSymbol']
            try:
                ctoken_asset = _compound_symbol_to_token(symbol=ctoken_symbol, timestamp=timestamp)
            except UnknownAsset:
                log.error(
                    f'Found unexpected cTokenSymbol {ctoken_symbol} during graph query. Skipping.')
                continue
            underlying_symbol = entry['underlyingSymbol']
            try:
                underlying_asset = symbol_to_asset_or_token(underlying_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected token symbol {underlying_symbol} during '
                    f'graph query. Skipping.',
                )
                continue

            # Amount/value of underlying asset paid by liquidator
            # Essentially liquidator covers part of the debt of the user
            debt_amount = FVal(entry['underlyingRepayAmount'])
            underlying_usd_price = query_usd_price_zero_if_error(
                asset=underlying_asset,
                time=timestamp,
                location='compound liquidation underlying asset',
                msg_aggregator=self.msg_aggregator,
            )
            debt_usd_value = debt_amount * underlying_usd_price
            # Amount/value of ctoken_asset lost to the liquidator
            # This is what the liquidator gains at a discount
            liquidated_amount = FVal(entry['amount'])
            liquidated_usd_price = query_usd_price_zero_if_error(
                asset=ctoken_asset,
                time=timestamp,
                location='compound liquidation ctoken asset',
                msg_aggregator=self.msg_aggregator,
            )
            liquidated_usd_value = liquidated_amount * liquidated_usd_price
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(
                    f'Found unprocessable liquidation id from the graph {entry["id"]}. Skipping',
                )
                continue

            gained_value = Balance(amount=debt_amount, usd_value=debt_usd_value)
            lost_value = Balance(amount=liquidated_amount, usd_value=liquidated_usd_value)
            events.append(CompoundEvent(
                event_type='liquidation',
                address=address,
                block_number=entry['blockNumber'],
                timestamp=timestamp,
                asset=underlying_asset,
                value=gained_value,
                to_asset=ctoken_asset,
                to_value=lost_value,
                realized_pnl=None,
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_lend_events(
            self,
            event_type: Literal['mint', 'redeem'],
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        param_types, param_values = get_common_params(from_ts, to_ts, address)
        if event_type == 'mint':
            graph_event_name = 'mintEvents'
            addr_position = 'to'
        elif event_type == 'redeem':
            graph_event_name = 'redeemEvents'
            addr_position = 'from'

        result = self.graph.query(  # type: ignore
            querystr=LEND_EVENTS_QUERY_PREFIX.format(
                graph_event_name=graph_event_name,
                addr_position=addr_position,
            ),
            param_types=param_types,
            param_values=param_values,
        )

        events = []
        for entry in result[graph_event_name]:
            ctoken_symbol = entry['cTokenSymbol']
            timestamp = entry['blockTime']
            try:
                ctoken_asset = _compound_symbol_to_token(symbol=ctoken_symbol, timestamp=timestamp)
            except UnknownAsset:
                log.error(
                    f'Found unexpected cTokenSymbol {ctoken_symbol} during graph query. Skipping.')
                continue

            underlying_symbol = ctoken_symbol[1:]
            try:
                underlying_asset = symbol_to_asset_or_token(underlying_symbol)
            except UnknownAsset:
                log.error(
                    f'Found unexpected token symbol {underlying_symbol} during '
                    f'graph query. Skipping.',
                )
                continue
            usd_price = query_usd_price_zero_if_error(
                asset=underlying_asset,
                time=timestamp,
                location=f'compound {event_type}',
                msg_aggregator=self.msg_aggregator,
            )
            underlying_amount = FVal(entry['underlyingAmount'])
            usd_value = underlying_amount * usd_price
            parse_result = _get_txhash_and_logidx(entry['id'])
            if parse_result is None:
                log.error(f'Found unprocessable mint id from the graph {entry["id"]}. Skipping')
                continue
            amount = FVal(entry['amount'])

            if event_type == 'mint':
                from_value = Balance(amount=underlying_amount, usd_value=usd_value)
                to_value = Balance(amount=amount, usd_value=usd_value)
                from_asset = underlying_asset
                to_asset = ctoken_asset
            else:  # redeem
                from_value = Balance(amount=amount, usd_value=usd_value)
                to_value = Balance(amount=underlying_amount, usd_value=usd_value)
                from_asset = ctoken_asset
                to_asset = underlying_asset  # type: ignore

            events.append(CompoundEvent(
                event_type=event_type,
                address=address,
                block_number=entry['blockNumber'],
                timestamp=timestamp,
                asset=from_asset,
                value=from_value,
                to_asset=to_asset,
                to_value=to_value,
                realized_pnl=None,
                tx_hash=parse_result[0],
                log_index=parse_result[1],
            ))

        return events

    def _get_comp_events(
            self,
            address: ChecksumEthAddress,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[CompoundEvent]:
        self.ethereum.get_blocknumber_by_time(from_ts)
        from_block = max(
            COMP_DEPLOYED_BLOCK,
            self.ethereum.get_blocknumber_by_time(from_ts),
        )
        argument_filters = {
            'from': COMPTROLLER_PROXY.address,
            'to': address,
        }
        comp_events = self.ethereum.get_logs(
            contract_address=A_COMP.ethereum_address,
            abi=ERC20TOKEN_ABI,
            event_name='Transfer',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=self.ethereum.get_blocknumber_by_time(to_ts),
        )

        events = []
        for event in comp_events:
            timestamp = self.ethereum.get_event_timestamp(event)
            amount = token_normalized_value(hexstr_to_int(event['data']), A_COMP)
            usd_price = query_usd_price_zero_if_error(
                asset=A_COMP,
                time=timestamp,
                location='comp_claim',
                msg_aggregator=self.msg_aggregator,
            )
            value = Balance(amount, amount * usd_price)
            events.append(CompoundEvent(
                event_type='comp',
                address=address,
                block_number=event['blockNumber'],
                timestamp=timestamp,
                asset=A_COMP,
                value=value,
                to_asset=None,
                to_value=None,
                realized_pnl=value,
                tx_hash=event['transactionHash'],
                log_index=event['logIndex'],
            ))

        return events

    def _process_events(
            self,
            events: List[CompoundEvent],
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Tuple[ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS]:
        """Processes all events and returns a dictionary of earned balances totals"""
        assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        rewards_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        profit_so_far: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_so_far: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        liquidation_profit: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        balances = self.get_balances(given_defi_balances)

        for idx, event in enumerate(events):
            if event.event_type == 'mint':
                assets[event.address][event.asset] -= event.value
            elif event.event_type == 'redeem':
                assert event.to_asset, 'redeem events should have a to_asset'
                assert event.to_value, 'redeem events should have a to_value'
                profit_amount = (
                    assets[event.address][event.to_asset].amount +
                    event.to_value.amount -
                    profit_so_far[event.address][event.to_asset].amount
                )
                profit: Optional[Balance]
                if profit_amount >= 0:
                    usd_price = query_usd_price_zero_if_error(
                        asset=event.to_asset,
                        time=event.timestamp,
                        location='comp redeem event processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    profit = Balance(profit_amount, profit_amount * usd_price)
                    profit_so_far[event.address][event.to_asset] += profit
                else:
                    profit = None

                assets[event.address][event.to_asset] += event.to_value
                events[idx] = event._replace(realized_pnl=profit)  # TODO: maybe not named tuple?

            elif event.event_type == 'borrow':
                loss_assets[event.address][event.asset] -= event.value
            elif event.event_type == 'repay':
                loss_amount = (
                    loss_assets[event.address][event.asset].amount +
                    event.value.amount -
                    loss_so_far[event.address][event.asset].amount
                )
                loss: Optional[Balance]
                if loss_amount >= 0:
                    usd_price = query_usd_price_zero_if_error(
                        asset=event.asset,
                        time=event.timestamp,
                        location='comp repay event processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    loss = Balance(loss_amount, loss_amount * usd_price)
                    loss_so_far[event.address][event.asset] += loss
                else:
                    loss = None

                loss_assets[event.address][event.asset] += event.value
                events[idx] = event._replace(realized_pnl=loss)  # TODO: maybe not named tuple?
            elif event.event_type == 'liquidation':
                assert event.to_asset, 'liquidation events should have a to_asset'
                # Liquidator covers part of the borrowed amount
                loss_assets[event.address][event.asset] += event.value
                liquidation_profit[event.address][event.asset] += event.value
                # Liquidator receives discounted to_asset
                loss_assets[event.address][event.to_asset] += event.to_value
                loss_so_far[event.address][event.to_asset] += event.to_value
            elif event.event_type == 'comp':
                rewards_assets[event.address][A_COMP] += event.value

        for address, bentry in balances.items():
            for asset, entry in bentry['lending'].items():
                profit_amount = (
                    profit_so_far[address][asset].amount +
                    entry.balance.amount +
                    assets[address][asset].amount
                )
                if profit_amount < 0:
                    log.error(
                        f'In compound we calculated negative profit. Should not happen. '
                        f'address: {address} asset: {asset} ',
                    )
                else:
                    usd_price = Inquirer().find_usd_price(asset)
                    profit_so_far[address][asset] = Balance(
                        amount=profit_amount,
                        usd_value=profit_amount * usd_price,
                    )

            for asset, entry in bentry['borrowing'].items():
                remaining = entry.balance + loss_assets[address][asset]
                if remaining.amount < ZERO:
                    continue
                loss_so_far[address][asset] += remaining
                if loss_so_far[address][asset].usd_value < ZERO:
                    amount = loss_so_far[address][asset].amount
                    loss_so_far[address][asset] = Balance(
                        amount=amount, usd_value=amount * Inquirer().find_usd_price(asset),
                    )

            for asset, entry in bentry['rewards'].items():
                rewards_assets[address][asset] += entry.balance

        return profit_so_far, loss_so_far, liquidation_profit, rewards_assets

    def get_history(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,  # pylint: disable=unused-argument
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Dict[str, Any]:
        """May raise:
        - RemoteError due to the graph query failure or etherscan
        """
        history: Dict[str, Any] = {}
        events: List[CompoundEvent] = []

        if self.graph is None:  # could not initialize graph
            return {}

        for address in addresses:
            user_events = self._get_lend_events('mint', address, from_timestamp, to_timestamp)
            user_events.extend(self._get_lend_events('redeem', address, from_timestamp, to_timestamp))  # noqa: E501
            user_events.extend(self._get_borrow_events('borrow', address, from_timestamp, to_timestamp))  # noqa: E501
            repay_events = self._get_borrow_events('repay', address, from_timestamp, to_timestamp)
            liquidation_events = self._get_liquidation_events(address, from_timestamp, to_timestamp)  # noqa: E501
            indices_to_remove = []
            for levent in liquidation_events:
                for ridx, revent in enumerate(repay_events):
                    if levent.tx_hash == revent.tx_hash:
                        indices_to_remove.append(ridx)

            for i in sorted(indices_to_remove, reverse=True):
                del repay_events[i]

            user_events.extend(repay_events)
            user_events.extend(liquidation_events)
            if len(user_events) != 0:
                # query comp events only if any other event has happened
                user_events.extend(self._get_comp_events(address, from_timestamp, to_timestamp))
                events.extend(user_events)

        events.sort(key=lambda x: x.timestamp)
        history['events'] = events
        profit, loss, liquidation, rewards = self._process_events(events, given_defi_balances)
        history['interest_profit'] = profit
        history['liquidation_profit'] = liquidation
        history['debt_loss'] = loss
        history['rewards'] = rewards

        return history

    def get_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: List[ChecksumEthAddress],
    ) -> List[DefiEvent]:
        history = self.get_history(
            given_defi_balances={},
            addresses=addresses,
            reset_db_data=False,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
        )

        events = []
        for event in history['events']:
            pnl = got_asset = got_balance = spent_asset = spent_balance = None  # noqa: E501
            if event.event_type == 'mint':
                spent_asset = event.asset
                spent_balance = event.value
                got_asset = event.to_asset
                got_balance = event.to_value
            elif event.event_type == 'redeem':
                spent_asset = event.asset
                spent_balance = event.value
                got_asset = event.to_asset
                got_balance = event.to_value
                if event.realized_pnl is not None:
                    pnl = [AssetBalance(asset=got_asset, balance=event.realized_pnl)]
            elif event.event_type == 'borrow':
                got_asset = event.asset
                got_balance = event.value
            elif event.event_type == 'repay':
                spent_asset = event.asset
                spent_balance = event.value
                if event.realized_pnl is not None:
                    pnl = [AssetBalance(asset=spent_asset, balance=-event.realized_pnl)]
            elif event.event_type == 'liquidation':
                spent_asset = event.to_asset
                spent_balance = event.to_value
                got_asset = event.asset
                got_balance = event.value
                pnl = [
                    # collateral lost
                    AssetBalance(asset=spent_asset, balance=-spent_balance),
                    # borrowed asset gained since you can keep it
                    AssetBalance(asset=got_asset, balance=got_balance),
                ]
            elif event.event_type == 'comp':
                got_asset = event.asset
                got_balance = event.value
                if event.realized_pnl is not None:
                    pnl = [AssetBalance(asset=got_asset, balance=event.realized_pnl)]
            else:
                raise AssertionError(f'Unexpected compound event {event.event_type}')

            events.append(DefiEvent(
                timestamp=event.timestamp,
                wrapped_event=event,
                event_type=DefiEventType.COMPOUND_EVENT,
                got_asset=got_asset,
                got_balance=got_balance,
                spent_asset=spent_asset,
                spent_balance=spent_balance,
                pnl=pnl,
                # Count all compound events in cost basis since there is a swap
                # from normal to cToken and back involved. Also to track debt.
                count_spent_got_cost_basis=True,
                tx_hash=event.tx_hash,
            ))

        return events

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List[AssetBalance]]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
