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
from rotkehlchen.utils.misc import ts_now, timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.chain.manager import ChainManager
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# eth transactions, external trades, ledger actions, uniswap trades, makerDAO DSR,
# makerDAO vaults, yearn vaults, compound, adex staking, aave lending
HISTORY_QUERY_STEPS = 10
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


class EventsHistorian():

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
        db_settings = self.db.get_settings()
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime
        self._reset_variables()

    def timestamp_to_date(self, timestamp: Timestamp) -> str:
        return timestamp_to_date(
            timestamp,
            formatstr=self.dateformat,
            treat_as_local=self.datelocaltime,
        )

    def _reset_variables(self) -> None:
        self.processing_state_name = 'Starting query of historical events'
        self.progress = ZERO
        db_settings = self.db.get_settings()
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime

    def _increase_progress(self, step: int, total_steps: int) -> int:
        step += 1
        self.progress = FVal(step / total_steps) * 100
        return step

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
        self._reset_variables()
        step = 0
        total_steps = len(self.exchange_manager.connected_exchanges) + HISTORY_QUERY_STEPS
        log.info(
            'Get/create trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )
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
                    # We need to have history of loans since before the range
                    start_ts=Timestamp(0),
                    end_ts=end_ts,
                ))

        def fail_history_cb(error_msg: str) -> None:
            """This callback will run for failure in exchange history query"""
            nonlocal empty_or_error
            empty_or_error += '\n' + error_msg

        for name, exchange in self.exchange_manager.connected_exchanges.items():
            self.processing_state_name = f'Querying {name} exchange history'
            exchange.query_history_with_callbacks(
                # We need to have history of exchanges since before the range
                start_ts=Timestamp(0),
                end_ts=end_ts,
                success_callback=populate_history_cb,
                fail_callback=fail_history_cb,
            )
            step = self._increase_progress(step, total_steps)

        try:
            self.processing_state_name = 'Querying ethereum transactions history'
            eth_transactions = self.chain_manager.ethereum.transactions.query(
                addresses=None,  # all addresses
                # We need to have history of transactions since before the range
                from_ts=Timestamp(0),
                to_ts=end_ts,
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
        step = self._increase_progress(step, total_steps)

        # Include the external trades in the history
        self.processing_state_name = 'Querying external trades history'
        external_trades = self.db.get_trades(
            # We need to have history of trades since before the range
            from_ts=Timestamp(0),
            to_ts=end_ts,
            location=Location.EXTERNAL,
        )
        history.extend(external_trades)
        step = self._increase_progress(step, total_steps)

        # include the ledger actions
        self.processing_state_name = 'Querying ledger actions history'
        ledger_actions, _ = self.query_ledger_actions(has_premium, from_ts=start_ts, to_ts=end_ts)
        step = self._increase_progress(step, total_steps)

        # include uniswap trades
        if has_premium and self.chain_manager.uniswap:
            self.processing_state_name = 'Querying uniswap history'
            uniswap_trades = self.chain_manager.uniswap.get_trades(
                addresses=self.chain_manager.queried_addresses_for_module('uniswap'),
                from_timestamp=Timestamp(0),
                to_timestamp=end_ts,
            )
            history.extend(uniswap_trades)
        step = self._increase_progress(step, total_steps)

        # Include makerdao DSR gains
        defi_events = []
        if self.chain_manager.makerdao_dsr and has_premium:
            self.processing_state_name = 'Querying makerDAO DSR history'
            dsr_gains = self.chain_manager.makerdao_dsr.get_dsr_gains_in_period(
                from_ts=start_ts,
                to_ts=end_ts,
            )
            for gain in dsr_gains:
                if gain.amount <= ZERO:
                    continue

                notes = (
                    f'MakerDAO DSR Gains from {self.timestamp_to_date(gain.from_timestamp)}'
                    f' to {self.timestamp_to_date(gain.to_timestamp)}'
                )
                defi_events.append(DefiEvent(
                    timestamp=gain.to_timestamp,
                    event_type=DefiEventType.DSR_LOAN_GAIN,
                    asset=A_DAI,
                    amount=gain.amount,
                    tx_hashes=gain.tx_hashes,
                    notes=notes,
                ))
        step = self._increase_progress(step, total_steps)

        # Include makerdao vault events
        if self.chain_manager.makerdao_vaults and has_premium:
            self.processing_state_name = 'Querying makerDAO vaults history'
            vault_details = self.chain_manager.makerdao_vaults.get_vault_details()
            # We count the loss on a vault in the period if the last event is within
            # the given period. It's not a very accurate approach but it's good enough
            # for now. A more detailed approach would need archive node or log querying
            # to find owed debt at any given timestamp
            for detail in vault_details:
                last_event_ts = detail.events[-1].timestamp
                if start_ts <= last_event_ts <= end_ts:
                    notes = (
                        f'USD value of DAI lost for MakerDAO vault {detail.identifier} '
                        f'due to accrued debt or liquidations. IMPORTANT: At the moment rotki '
                        f'can\'t figure debt until a given time, so this is debt until '
                        f'now. If you are looking at a past range this may be bigger '
                        f'than it should be. We are actively working on improving this'
                    )
                    defi_events.append(DefiEvent(
                        timestamp=last_event_ts,
                        event_type=DefiEventType.MAKERDAO_VAULT_LOSS,
                        asset=A_USD,
                        amount=detail.total_liquidated.usd_value + detail.total_interest_owed,
                        tx_hashes=[x.tx_hash for x in detail.events],
                        notes=notes,
                    ))
        step = self._increase_progress(step, total_steps)

        # include yearn vault events
        if self.chain_manager.yearn_vaults and has_premium:
            self.processing_state_name = 'Querying yearn vaults history'
            yearn_vaults_history = self.chain_manager.yearn_vaults.get_history(
                given_defi_balances=self.chain_manager.defi_balances,
                addresses=self.chain_manager.queried_addresses_for_module('yearn_vaults'),
                reset_db_data=False,
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            )
            for address, vault_mappings in yearn_vaults_history.items():
                for vault_name, vault_history in vault_mappings.items():
                    # For the vaults since we can't get historical values of vault tokens
                    # yet, for the purposes of the tax report count everything as USD
                    for yearn_event in vault_history.events:
                        if start_ts <= yearn_event.timestamp <= end_ts and yearn_event.realized_pnl is not None:  # noqa: E501
                            defi_events.append(DefiEvent(
                                timestamp=yearn_event.timestamp,
                                event_type=DefiEventType.YEARN_VAULTS_PNL,
                                asset=A_USD,
                                amount=yearn_event.realized_pnl.usd_value,
                                tx_hashes=[yearn_event.tx_hash],
                                notes=(
                                    f'USD equivalent PnL for {address} and yearn '
                                    f'{vault_name} at event'
                                ),
                            ))
        step = self._increase_progress(step, total_steps)

        # include compound events
        if self.chain_manager.compound and has_premium:
            self.processing_state_name = 'Querying compound history'
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
                        tx_hashes=[event.tx_hash],
                        notes=(
                            f'Interest earned in compound for '
                            f'{event.to_asset.identifier} until this event'
                        ),
                    ))
                elif event.event_type == 'repay':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_DEBT_REPAY,
                        asset=event.asset,
                        amount=event.realized_pnl.amount,
                        tx_hashes=[event.tx_hash],
                        notes=(
                            f'Amount of {event.asset.identifier} lost in '
                            f'compound due to debt repayment'
                        ),
                    ))
                elif event.event_type == 'liquidation':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_LIQUIDATION_DEBT_REPAID,
                        asset=event.asset,
                        amount=event.value.amount,
                        tx_hashes=[event.tx_hash],
                        notes=(
                            f'Amount of {event.asset.identifier} gained in '
                            f'compound due to liquidation debt repayment'
                        ),
                    ))
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_LIQUIDATION_COLLATERAL_LOST,
                        asset=event.to_asset,
                        amount=event.to_value.amount,
                        tx_hashes=[event.tx_hash],
                        notes=(
                            f'Amount of {event.to_asset.identifier} collateral lost '
                            f'in compound due to liquidation'
                        ),
                    ))
                elif event.event_type == 'comp':
                    defi_events.append(DefiEvent(
                        timestamp=event.timestamp,
                        event_type=DefiEventType.COMPOUND_REWARDS,
                        asset=event.asset,
                        amount=event.realized_pnl.amount,
                        tx_hashes=[event.tx_hash],
                    ))
        step = self._increase_progress(step, total_steps)

        # include adex staking profit
        adex = self.chain_manager.adex
        if adex is not None and has_premium:
            self.processing_state_name = 'Querying adex staking history'
            adx_mapping = adex.get_events_history(
                addresses=self.chain_manager.queried_addresses_for_module('adex'),
                reset_db_data=False,
                from_timestamp=start_ts,
                to_timestamp=end_ts,
            )
            for _, adex_history in adx_mapping.items():
                # The transaction hashes here are not accurate. Need to figure out
                # a way to have accurate transaction hashes for events in a time period
                adex_tx_hashes = [x.tx_hash for x in adex_history.events]
                for adx_detail in adex_history.staking_details:
                    defi_events.append(DefiEvent(
                        timestamp=end_ts,
                        event_type=DefiEventType.ADEX_STAKE_PROFIT,
                        asset=A_ADX,
                        amount=adx_detail.adx_profit_loss.amount,
                        tx_hashes=adex_tx_hashes,  # type: ignore
                    ))
                    defi_events.append(DefiEvent(
                        timestamp=end_ts,
                        event_type=DefiEventType.ADEX_STAKE_PROFIT,
                        asset=A_DAI,
                        amount=adx_detail.dai_profit_loss.amount,
                        tx_hashes=adex_tx_hashes,  # type: ignore
                    ))
        step = self._increase_progress(step, total_steps)

        # include aave lending events
        aave = self.chain_manager.aave
        if aave is not None and has_premium:
            self.processing_state_name = 'Querying aave history'
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
                            tx_hashes=[event.tx_hash],
                        ))
                        total_amount_per_token[event.asset] += event.value.amount

                # TODO: Here we should also calculate any unclaimed interest payments
                # within the time range. IT's quite complicated to do that though and
                # would most probably require an archive node

                # Add all losses from aave borrowing/liquidations
                for asset, balance in aave_history.total_lost.items():
                    aave_tx_hashes = []
                    for event in aave_history.events:
                        if event not in ('borrow', 'repay', 'liquidation'):
                            continue

                        if event in ('borrow', 'repay') and event.asset == asset:
                            aave_tx_hashes.append(event.tx_hash)
                            continue

                        relevant_liquidation = (
                            event.event_type == 'liquidation' and
                            asset in (event.collateral_asset, event.principal_asset)
                        )
                        if relevant_liquidation:
                            aave_tx_hashes.append(event.tx_hash)

                    defi_events.append(DefiEvent(
                        timestamp=now,
                        event_type=DefiEventType.AAVE_LOSS,
                        asset=asset,
                        amount=balance.amount,
                        tx_hashes=aave_tx_hashes,
                        notes=(
                            f'All {asset.identifier} lost in Aave due to borrowing '
                            f'debt or liquidations in the PnL period.'
                        ),
                    ))

                # Add earned assets from aave liquidations
                for asset, balance in aave_history.total_earned_liquidations.items():
                    aave_tx_hashes = []
                    for event in aave_history.events:
                        relevant_liquidation = (
                            event.event_type == 'liquidation' and
                            asset in (event.collateral_asset, event.principal_asset)
                        )
                        if relevant_liquidation:
                            aave_tx_hashes.append(event.tx_hash)

                    defi_events.append(DefiEvent(
                        timestamp=now,
                        event_type=DefiEventType.AAVE_LOAN_INTEREST,
                        asset=asset,
                        amount=balance.amount,
                        tx_hashes=aave_tx_hashes,
                        notes=(
                            f'All {asset.identifier} gained in Aave due to liquidation leftovers'
                        ),
                    ))
        self._increase_progress(step, total_steps)
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
