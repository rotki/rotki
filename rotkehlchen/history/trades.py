import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from rotkehlchen.accounting.structures import DefiEvent, DefiEventType, LedgerAction
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.constants.assets import A_ADX, A_DAI, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, Loan, MarginPosition, Trade
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.exchanges.poloniex import process_polo_loans
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import EthereumTransaction, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import action_get_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.manager import ChainManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


FREE_LEDGER_ACTIONS_LIMIT = 50

HistoryResult = Tuple[
    str,
    List[Union[Trade, MarginPosition, AMMTrade]],
    List[Loan],
    List[AssetMovement],
    List[EthereumTransaction],
    List[DefiEvent],
    List[LedgerAction],
]


def limit_trade_list_to_period(
        trades_list: List[Union[Trade, MarginPosition]],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[Union[Trade, MarginPosition]]:
    """Accepts a SORTED by timestamp trades_list and returns a shortened version
    of that list limited to a specific time period"""

    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    for idx, trade in enumerate(trades_list):
        timestamp = action_get_timestamp(trade)
        if start_idx is None and timestamp >= start_ts:
            start_idx = idx

        if end_idx is None and timestamp > end_ts:
            end_idx = idx if idx >= 1 else 0
            break

    return trades_list[start_idx:end_idx] if start_idx is not None else []


class TradesHistorian():

    def __init__(
            self,
            user_directory: Path,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            exchange_manager: ExchangeManager,
            chain_manager: 'ChainManager',
    ) -> None:

        self.msg_aggregator = msg_aggregator
        self.user_directory = user_directory
        self.db = db
        self.exchange_manager = exchange_manager
        self.chain_manager = chain_manager

    def query_ledger_actions(
            self,
            has_premium: bool,
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            location: Optional[Location] = None,
    ) -> Tuple[List[LedgerAction], int]:
        """Queries the ledger actions from the DB and applies the free version limit

        TODO: Since we always query all in one call, the limiting will work, but if we start
        batch querying by time then we need to amend the logic of limiting here.
        Would need to use the same logic we do with trades. Using db entries count
        and count what all calls return and what is sums up to
        """
        db = DBLedgerActions(self.db, self.msg_aggregator)
        actions = db.get_ledger_actions(from_ts=from_ts, to_ts=to_ts, location=location)
        original_length = len(actions)
        if has_premium is False:
            actions = actions[:FREE_LEDGER_ACTIONS_LIMIT]

        return actions, original_length

    def get_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            has_premium: bool,
    ) -> HistoryResult:
        """Creates trades and loans history from start_ts to end_ts"""
        log.info(
            'Get/create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        now = ts_now()
        # start creating the all trades history list
        history: List[Union[Trade, MarginPosition, AMMTrade]] = []
        asset_movements = []
        loans = []
        empty_or_error = ''

        def populate_history_cb(
                trades_history: List[Trade],
                margin_history: List[MarginPosition],
                result_asset_movements: List[AssetMovement],
                exchange_specific_data: Any,
        ) -> None:
            """This callback will run for succesfull exchange history query"""
            history.extend(trades_history)
            history.extend(margin_history)
            asset_movements.extend(result_asset_movements)

            if exchange_specific_data:
                # This can only be poloniex at the moment
                polo_loans_data = exchange_specific_data
                loans.extend(process_polo_loans(
                    msg_aggregator=self.msg_aggregator,
                    data=polo_loans_data,
                    # We need to have full history of loans available
                    start_ts=Timestamp(0),
                    end_ts=now,
                ))

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        for _, exchange in self.exchange_manager.connected_exchanges.items():
            exchange.query_history_with_callbacks(
                # We need to have full history of exchanges available
                start_ts=Timestamp(0),
                end_ts=now,
                success_callback=populate_history_cb,
                fail_callback=fail_history_cb,
            )

        try:
            eth_transactions = self.chain_manager.ethereum.transactions.query(
                addresses=None,  # all addresses
                # We need to have full history of transactions available
                from_ts=Timestamp(0),
                to_ts=now,
                with_limit=False,  # at the moment ignore the limit for historical processing,
                recent_first=False,  # for history processing we need oldest first
            )
        except RemoteError as e:
            eth_transactions = []
            msg = str(e)
            self.msg_aggregator.add_error(
                f'There was an error when querying etherscan for ethereum transactions: {msg}'
                f'The final history result will not include ethereum transactions',
            )
            empty_or_error += '\n' + msg

        # Include the external trades in the history
        external_trades = self.db.get_trades(
            # We need to have full history of trades available
            from_ts=Timestamp(0),
            to_ts=now,
            location=Location.EXTERNAL,
        )
        history.extend(external_trades)

        # include the ledger actions
        ledger_actions, _ = self.query_ledger_actions(has_premium, from_ts=start_ts, to_ts=end_ts)

        # include uniswap trades
        if has_premium and self.chain_manager.uniswap:
            uniswap_trades = self.chain_manager.uniswap.get_trades(
                addresses=self.chain_manager.queried_addresses_for_module('uniswap'),
                from_timestamp=Timestamp(0),
                to_timestamp=now,
            )
            history.extend(uniswap_trades)

        # Include makerdao DSR gains
        defi_events = []
        if self.chain_manager.makerdao_dsr and has_premium:
            dsr_gains = self.chain_manager.makerdao_dsr.get_dsr_gains_in_period(
                from_ts=start_ts,
                to_ts=end_ts,
            )
            for gain, timestamp in dsr_gains:
                if gain > ZERO:
                    defi_events.append(DefiEvent(
                        timestamp=timestamp,
                        event_type=DefiEventType.DSR_LOAN_GAIN,
                        asset=A_DAI,
                        amount=gain,
                    ))

        # Include makerdao vault events
        if self.chain_manager.makerdao_vaults and has_premium:
            vault_details = self.chain_manager.makerdao_vaults.get_vault_details()
            # We count the loss on a vault in the period if the last event is within
            # the given period. It's not a very accurate approach but it's good enough
            # for now. A more detailed approach would need archive node or log querying
            # to find owed debt at any given timestamp
            for detail in vault_details:
                last_event_ts = detail.events[-1].timestamp
                if start_ts <= last_event_ts <= end_ts:
                    defi_events.append(DefiEvent(
                        timestamp=last_event_ts,
                        event_type=DefiEventType.MAKERDAO_VAULT_LOSS,
                        asset=A_USD,
                        amount=detail.total_liquidated.usd_value + detail.total_interest_owed,
                    ))

        # include yearn vault events
        if self.chain_manager.yearn_vaults and has_premium:
            yearn_vaults_history = self.chain_manager.yearn_vaults.get_history(
                given_defi_balances=self.chain_manager.defi_balances,
                addresses=self.chain_manager.queried_addresses_for_module('yearn_vaults'),
                reset_db_data=False,
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            )
            for _, vault_mappings in yearn_vaults_history.items():
                for _, vault_history in vault_mappings.items():
                    # For the vaults since we can't get historical values of vault tokens
                    # yet, for the purposes of the tax report count everything as USD
                    defi_events.append(DefiEvent(
                        timestamp=Timestamp(end_ts - 1),
                        event_type=DefiEventType.YEARN_VAULTS_PNL,
                        asset=A_USD,
                        amount=vault_history.profit_loss.usd_value,
                    ))

        # include compound events
        if self.chain_manager.compound and has_premium:
            compound_history = self.chain_manager.compound.get_history(
                given_defi_balances=self.chain_manager.defi_balances,
                addresses=self.chain_manager.queried_addresses_for_module('compound'),
                reset_db_data=False,
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            )
            for event in compound_history['events']:
                skip_event = (
                    event.event_type != 'liquidation' and
                    (event.realized_pnl is None or event.realized_pnl.amount == ZERO)
                )
                if skip_event:
                    continue  # skip events with no realized profit/loss

                if event.event_type == 'redeem':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_LOAN_INTEREST,
                        asset=event.to_asset,
                        amount=event.realized_pnl.amount,
                    ))
                elif event.event_type == 'repay':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_DEBT_REPAY,
                        asset=event.asset,
                        amount=event.realized_pnl.amount,
                    ))
                elif event.event_type == 'liquidation':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_LIQUIDATION_DEBT_REPAID,
                        asset=event.asset,
                        amount=event.value.amount,
                    ))
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_LIQUIDATION_COLLATERAL_LOST,
                        asset=event.to_asset,
                        amount=event.to_value.amount,
                    ))
                elif event.event_type == 'comp':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_REWARDS,
                        asset=event.asset,
                        amount=event.realized_pnl.amount,
                    ))

        # include adex staking profit
        adex = self.chain_manager.adex
        if adex is not None and has_premium:
            adx_mapping = adex.get_events_history(
                addresses=self.chain_manager.queried_addresses_for_module('adex'),
                reset_db_data=False,
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            )
            for _, adex_history in adx_mapping.items():
                for adx_detail in adex_history.staking_details:
                    defi_events.append(DefiEvent(
                        timestamp=end_ts,
                        event_type=DefiEventType.ADEX_STAKE_PROFIT,
                        asset=A_ADX,
                        amount=adx_detail.adx_profit_loss.amount,
                    ))
                    defi_events.append(DefiEvent(
                        timestamp=end_ts,
                        event_type=DefiEventType.ADEX_STAKE_PROFIT,
                        asset=A_DAI,
                        amount=adx_detail.dai_profit_loss.amount,
                    ))

        # include aave lending events
        aave = self.chain_manager.aave
        if aave is not None and has_premium:
            mapping = aave.get_history(
                given_defi_balances=self.chain_manager.defi_balances,
                addresses=self.chain_manager.queried_addresses_for_module('aave'),
                reset_db_data=False,
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            )

            now = ts_now()
            for _, aave_history in mapping.items():
                total_amount_per_token: Dict[Asset, FVal] = defaultdict(FVal)
                for event in aave_history.events:
                    if event.timestamp < start_ts:
                        continue
                    if event.timestamp > end_ts:
                        break

                    if event.event_type == 'interest':
                        defi_events.append(DefiEvent(
                            timestamp=event.timestamp,
                            event_type=DefiEventType.AAVE_LOAN_INTEREST,
                            asset=event.asset,
                            amount=event.value.amount,
                        ))
                        total_amount_per_token[event.asset] += event.value.amount

                for token, balance in aave_history.total_earned_interest.items():
                    # Αdd an extra event per token per address for the remaining not paid amount
                    if token in total_amount_per_token:
                        defi_events.append(DefiEvent(
                            timestamp=now,
                            event_type=DefiEventType.AAVE_LOAN_INTEREST,
                            asset=token,
                            amount=balance.amount - total_amount_per_token[token],
                        ))

                # Add all losses from aave borrowing/liquidations
                for asset, balance in aave_history.total_lost.items():
                    defi_events.append(DefiEvent(
                        timestamp=now,
                        event_type=DefiEventType.AAVE_LOSS,
                        asset=asset,
                        amount=balance.amount,
                    ))

                # Add earned assets from aave liquidations
                for asset, balance in aave_history.total_earned_liquidations.items():
                    defi_events.append(DefiEvent(
                        timestamp=now,
                        event_type=DefiEventType.AAVE_LOAN_INTEREST,
                        asset=asset,
                        amount=balance.amount,
                    ))

        history.sort(key=action_get_timestamp)
        return (
            empty_or_error,
            history,
            loans,
            asset_movements,
            eth_transactions,
            defi_events,
            ledger_actions,
        )
