import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union, cast

import gevent

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT
from rotkehlchen.accounting.events import TaxableEvents
from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures import ActionType, DefiEvent, HistoryBaseEntry
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors import (
    NoPriceForGivenTimestamp,
    PriceQueryUnsupportedAsset,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Loan,
    MarginPosition,
    Trade,
    TradeType,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import EthereumTransaction, Fee, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import (
    TaxableAction,
    action_get_assets,
    action_get_identifier,
    action_get_timestamp,
    action_get_type,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Accountant():

    def __init__(
            self,
            db: 'DBHandler',
            user_directory: Path,
            msg_aggregator: MessagesAggregator,
            evm_tx_decoder: 'EVMTransactionDecoder',
            create_csv: bool,
            premium: Optional[Premium],
    ) -> None:
        self.db = db
        profit_currency = db.get_main_currency()
        self.msg_aggregator = msg_aggregator
        self.csvexporter = CSVExporter(
            database=db,
            user_directory=user_directory,
            create_csv=create_csv,
        )
        self.events = TaxableEvents(
            csv_exporter=self.csvexporter,
            evm_tx_decoder=evm_tx_decoder,
            profit_currency=profit_currency,
            msg_aggregator=msg_aggregator,
        )

        self.asset_movement_fees = FVal(0)
        self.currently_processing_timestamp = -1
        self.first_processed_timestamp = -1
        self.premium = premium

    def __del__(self) -> None:
        del self.events
        del self.csvexporter

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium

    def deactivate_premium_status(self) -> None:
        self.premium = None

    def _customize(self, settings: DBSettings) -> None:
        """Customize parameters after pulling DBSettings"""
        if settings.include_crypto2crypto is not None:
            self.events.base.include_crypto2crypto = settings.include_crypto2crypto

        if settings.taxfree_after_period is None:
            self.events.base.taxfree_after_period = None
        else:
            given_taxfree_after_period: Optional[int] = settings.taxfree_after_period
            if given_taxfree_after_period == -1:
                # That means user requested to disable taxfree_after_period
                given_taxfree_after_period = None

            self.events.base.taxfree_after_period = given_taxfree_after_period

        self.profit_currency = settings.main_currency
        self.events.base.profit_currency = settings.main_currency
        self.events.taxable_ledger_actions = settings.taxable_ledger_actions
        self.csvexporter.profit_currency = settings.main_currency

        if settings.account_for_assets_movements is not None:
            self.events.account_for_assets_movements = settings.account_for_assets_movements

    def get_fee_in_profit_currency(self, trade: Trade) -> Fee:
        """Get the profit_currency rate of the fee of the given trade

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from all price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the price oracle
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        if trade.fee_currency is None or trade.fee is None:
            return Fee(ZERO)

        fee_rate = PriceHistorian().query_historical_price(
            from_asset=trade.fee_currency,
            to_asset=self.profit_currency,
            timestamp=trade.timestamp,
        )
        return Fee(fee_rate * trade.fee)

    def add_asset_movement_to_events(self, movement: AssetMovement) -> None:
        """
        Adds the given asset movement to the processed events

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from all price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        timestamp = movement.timestamp
        if timestamp < self.start_ts:
            return

        if movement.asset.identifier == 'KFEE' or not self.events.account_for_assets_movements:
            # There is no reason to process deposits of KFEE for kraken as it has only value
            # internal to kraken and KFEE has no value and will error at cryptocompare price query
            return

        fee_rate = self.events.base.get_rate_in_profit_currency(movement.fee_asset, timestamp)
        cost = movement.fee * fee_rate
        self.asset_movement_fees += cost
        log.debug(
            'Accounting for asset movement',
            category=movement.category,
            asset=movement.asset,
            cost_in_profit_currency=cost,
            timestamp=timestamp,
            exchange_name=movement.location,
        )

        self.csvexporter.add_asset_movement(
            exchange=movement.location,
            category=movement.category,
            asset=movement.asset,
            fee=movement.fee,
            rate=fee_rate,
            timestamp=timestamp,
            link=movement.link,
        )

    def trade_add_to_sell_events(self, trade: Trade, loan_settlement: bool) -> None:
        """
        Adds the given trade to the sell events

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from all price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        selling_asset = trade.base_asset
        receiving_asset = trade.quote_asset
        receiving_asset_rate = self.events.base.get_rate_in_profit_currency(
            receiving_asset,
            trade.timestamp,
        )
        selling_rate = receiving_asset_rate * trade.rate
        fee_in_profit_currency = self.get_fee_in_profit_currency(trade)
        gain_in_profit_currency = selling_rate * trade.amount

        if not loan_settlement:
            self.events.base.add_sell_and_corresponding_buy(
                location=trade.location,
                selling_asset=selling_asset,
                selling_amount=trade.amount,
                receiving_asset=receiving_asset,
                receiving_amount=trade.amount * trade.rate,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=trade.fee_currency,
                fee_amount=trade.fee,
                trade_rate=trade.rate,
                rate_in_profit_currency=selling_rate,
                timestamp=trade.timestamp,
                link=trade.link,
                notes=trade.notes,
            )
        else:
            self.events.base.add_sell(
                location=trade.location,
                selling_asset=selling_asset,
                selling_amount=trade.amount,
                receiving_asset=None,
                receiving_amount=None,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=trade.fee_currency,
                fee_amount=trade.fee,
                rate_in_profit_currency=selling_rate,
                timestamp=trade.timestamp,
                loan_settlement=True,
                is_virtual=False,
                link=trade.link,
                notes=trade.notes,
            )

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            trade_history: List[Union[Trade, MarginPosition, AMMTrade]],
            loan_history: List[Loan],
            asset_movements: List[AssetMovement],
            defi_events: List[DefiEvent],
            ledger_actions: List[LedgerAction],
            history_events: List[HistoryBaseEntry],
    ) -> int:
        """Processes the entire history of cryptoworld actions in order to determine
        the price and time at which every asset was obtained and also
        the general and taxable profit/loss.

        start_ts here is the timestamp at which to start taking trades and other
        taxable events into account. Not where processing starts from. Processing
        always starts from the very first event we find in the history.

        Returns the id of the generated report
        """
        active_premium = self.premium and self.premium.is_active()
        log.info(
            'Start of history processing',
            start_ts=start_ts,
            end_ts=end_ts,
            active_premium=active_premium,
        )
        events_limit = -1 if active_premium else FREE_PNL_EVENTS_LIMIT
        profit_currency = self.db.get_main_currency()
        self.events.reset(profit_currency=profit_currency, start_ts=start_ts, end_ts=end_ts)
        self.start_ts = start_ts
        self.asset_movement_fees = FVal(0)
        self.csvexporter.reset()

        # Ask the DB for the settings once at the start of processing so we got the
        # same settings through the entire task
        db_settings = self.db.get_settings()
        self._customize(db_settings)

        actions: List[TaxableAction] = list(trade_history)
        # If we got loans, we need to interleave them with the full history and re-sort
        if len(loan_history) != 0:
            actions.extend(loan_history)

        if len(asset_movements) != 0:
            actions.extend(asset_movements)

        if len(defi_events) != 0:
            actions.extend(defi_events)

        if len(ledger_actions) != 0:
            actions.extend(ledger_actions)

        if len(history_events) != 0:
            actions.extend(history_events)

        actions.sort(key=action_get_timestamp)
        # The first ts is the ts of the first action we have in history or 0 for empty history
        first_ts = Timestamp(0) if len(actions) == 0 else action_get_timestamp(actions[0])
        self.currently_processing_timestamp = first_ts
        self.first_processed_timestamp = first_ts
        # Create a new pnl report in the DB to be used to save each event generated
        report_id = self.csvexporter.create_pnlreport_in_db(
            first_processed_timestamp=self.first_processed_timestamp,
            start_ts=start_ts,
            end_ts=end_ts,
            profit_currency=self.profit_currency,
            settings=db_settings,
        )

        prev_time = Timestamp(0)
        count = 0
        actions_length = len(actions)
        last_event_ts = Timestamp(0)
        ignored_actionids_mapping = self.db.get_ignored_action_ids(action_type=None)
        actions_iter = iter(actions)
        while True:
            try:
                (
                    processed_actions_num,
                    prev_time,
                ) = self._process_action(
                    actions_iterator=actions_iter,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    prev_time=prev_time,
                    db_settings=db_settings,
                    ignored_actionids_mapping=ignored_actionids_mapping,
                )
            except PriceQueryUnsupportedAsset as e:
                action = actions[count]
                ts = action_get_timestamp(action)
                self.msg_aggregator.add_error(
                    f'Skipping action with id "{action_get_identifier(action)}" at '
                    f'{self.csvexporter.timestamp_to_date(ts)} '
                    f'during history processing due to an asset unknown to '
                    f'cryptocompare being involved. Check logs for details',
                )
                log.error(
                    f'Skipping action during history processing due to '
                    f'cryptocompare not supporting an involved asset: {str(e)}',
                )
                count += 1
                continue
            except NoPriceForGivenTimestamp as e:
                action = actions[count]
                ts = action_get_timestamp(action)
                self.msg_aggregator.add_error(
                    f'Skipping action with id "{action_get_identifier(action)}" at '
                    f'{self.csvexporter.timestamp_to_date(ts)} '
                    f'during history processing due to inability to find a price '
                    f'at that point in time: {str(e)}. Check the logs for more details',
                )
                log.error(
                    f'Skipping action {str(action)} during history processing due to '
                    f'inability to query a price at that time: {str(e)}',
                )
                count += 1
                continue
            except RemoteError as e:
                action = actions[count]
                ts = action_get_timestamp(action)
                self.msg_aggregator.add_error(
                    f'Skipping action with id "{action_get_identifier(action)}" at '
                    f'{self.csvexporter.timestamp_to_date(ts)} '
                    f'during history processing due to inability to reach an external '
                    f'service at that point in time: {str(e)}. Check the logs for more details',
                )
                log.error(
                    f'Skipping action {str(action)} during history processing due to '
                    f'inability to reach an external service at that time: {str(e)}',
                )
                count += 1
                continue

            if processed_actions_num == 0:
                actions_length = count
                break  # we reached the period end

            last_event_ts = prev_time
            if count % 500 == 0:
                # This loop can take a very long time depending on the amount of actions
                # to process. We need to yield to other greenlets or else calls to the
                # API may time out
                gevent.sleep(0.5)
            count += processed_actions_num
            if not active_premium and count >= FREE_PNL_EVENTS_LIMIT:
                log.debug(
                    f'PnL reports event processing has hit the event limit of {events_limit}. '
                    f'Processing stopped and the results will not '
                    f'take into account subsequent events. Total events were {len(actions)}',
                )
                break

        self.events.csv_exporter.maybe_add_summary(pnls=self.events.base.pnls)
        dbpnl = DBAccountingReports(self.csvexporter.database)
        dbpnl.add_report_overview(
            report_id=report_id,
            last_processed_timestamp=last_event_ts,
            processed_actions=count,
            total_actions=actions_length,
            pnls=self.events.base.pnls,
        )

        return report_id

    @staticmethod
    def _should_ignore_action(
            action: TaxableAction,
            action_type: str,
            ignored_actionids_mapping: Dict[ActionType, List[str]],
    ) -> Tuple[bool, Optional[str]]:
        # TODO: These ifs/mappings of action type str to the enum
        # are only due to mix of new and old code. They should be removed and only
        # the enum should be used everywhere eventually
        should_ignore = False
        identifier: Optional[str] = None
        if action_type == 'trade':
            trade = cast(Trade, action)
            identifier = trade.identifier
            should_ignore = identifier in ignored_actionids_mapping.get(ActionType.TRADE, [])

        elif action_type == 'asset_movement':
            movement = cast(AssetMovement, action)
            identifier = movement.identifier
            should_ignore = identifier in ignored_actionids_mapping.get(
                ActionType.ASSET_MOVEMENT, [],
            )

        elif action_type == 'ethereum_transaction':
            tx = cast(EthereumTransaction, action)
            identifier = tx.identifier
            should_ignore = tx.identifier in ignored_actionids_mapping.get(
                ActionType.ETHEREUM_TRANSACTION, [],
            )

        elif action_type == 'ledger_action':
            ledger_action = cast(LedgerAction, action)
            # Ignored actions have TEXT type in the database but
            # ledger actions have int as type for identifier
            identifier = str(ledger_action.identifier)
            should_ignore = identifier in ignored_actionids_mapping.get(
                ActionType.LEDGER_ACTION, [],
            )

        return should_ignore, identifier

    def _process_action(
            self,
            actions_iterator: Iterator[TaxableAction],
            start_ts: Timestamp,
            end_ts: Timestamp,
            prev_time: Timestamp,
            db_settings: DBSettings,
            ignored_actionids_mapping: Dict[ActionType, List[str]],
    ) -> Tuple[int, Timestamp]:
        """Processes each individual action and returns a tuple with processing information:
        - How many actions were consumed (0 to indicate we finished processing)
        - last action timestamp

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the price oracle
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        ignored_assets = self.db.get_ignored_assets()
        action = next(actions_iterator, None)
        if action is None:
            return 0, prev_time

        # Assert we are sorted in ascending time order.
        timestamp = action_get_timestamp(action)
        assert timestamp >= prev_time, (
            'During history processing the trades/loans are not in ascending order'
        )
        prev_time = timestamp

        if not db_settings.calculate_past_cost_basis and timestamp < start_ts:
            # ignore older actions than start_ts if we don't want past cost basis
            return 1, prev_time

        if timestamp > end_ts:
            # reached the end of the time period for the report
            return 0, prev_time

        self.currently_processing_timestamp = timestamp
        action_type = action_get_type(action)

        try:
            action_assets = action_get_assets(action)
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'At history processing found trade with unknown asset {e.asset_name}. '
                f'Ignoring the trade.',
            )
            return 1, prev_time
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'At history processing found trade with unsupported asset {e.asset_name}. '
                f'Ignoring the trade.',
            )
            return 1, prev_time
        except UnprocessableTradePair as e:
            self.msg_aggregator.add_error(
                f'At history processing found trade with unprocessable trade pair {str(e)} '
                f'Ignoring the trade.',
            )
            return 1, prev_time

        if any(x in ignored_assets for x in action_assets):
            log.debug(
                'Ignoring action with ignored asset',
                action_type=action_type,
                assets=[x.identifier for x in action_assets],
            )
            return 1, prev_time

        should_ignore, identifier = self._should_ignore_action(
            action=action,
            action_type=action_type,
            ignored_actionids_mapping=ignored_actionids_mapping,
        )
        if should_ignore:
            log.info(
                f'Ignoring {action_type} action with identifier {identifier} '
                f'at {timestamp} since the user asked to ignore it',
            )
            return 1, prev_time

        if action_type == 'loan':
            action = cast(Loan, action)
            self.events.add_loan_gain(
                location=action.location,
                gained_asset=action.currency,
                lent_amount=action.amount_lent,
                gained_amount=action.earned,
                fee_in_asset=action.fee,
                open_time=action.open_time,
                close_time=timestamp,
                link=None,
                notes=None,
            )
            return 1, prev_time
        if action_type == 'asset_movement':
            action = cast(AssetMovement, action)
            self.add_asset_movement_to_events(action)
            return 1, prev_time
        if action_type == 'margin_position':
            action = cast(MarginPosition, action)
            self.events.add_margin_position(margin=action)
            return 1, prev_time
        if action_type == 'defi_event':
            action = cast(DefiEvent, action)
            self.events.add_defi_event(action)
            return 1, prev_time
        if action_type == 'ledger_action':
            action = cast(LedgerAction, action)
            self.events.add_ledger_action(action)
            return 1, prev_time
        if action_type == 'history_base_entry':
            action = cast(HistoryBaseEntry, action)
            consumed_events = self.events.add_history_base_entry(action, actions_iterator)
            return consumed_events, prev_time

        if isinstance(action, AMMTrade) and action.tx_hash:
            link = f'{self.csvexporter.eth_explorer}{action.tx_hash}'
        elif hasattr(action, 'link') and action.link:  # type: ignore
            link = action.link  # type: ignore
        else:
            link = ''

        if hasattr(action, 'note'):
            notes = action.notes  # type: ignore
        else:
            notes = ''

        # if we get here it's a trade
        trade = cast(Trade, action)
        # When you buy, you buy with the cost_currency and receive the other one
        # When you sell, you sell the amount in non-cost_currency and receive
        # costs in cost_currency

        if trade.rate == ZERO:
            msg = (
                f'Ignoring {str(trade)} because has a rate value of 0. '
                f'This entry should be updated in the database.'
            )

            self.msg_aggregator.add_warning(msg)
            return 1, prev_time

        if trade.trade_type == TradeType.BUY:
            self.events.base.add_buy_and_corresponding_sell(
                location=trade.location,
                bought_asset=trade.base_asset,
                bought_amount=trade.amount,
                paid_with_asset=trade.quote_asset,
                trade_rate=trade.rate,
                fee_in_profit_currency=self.get_fee_in_profit_currency(trade),
                fee_currency=trade.fee_currency,
                fee_amount=trade.fee,
                timestamp=trade.timestamp,
                link=link,
                notes=notes,
            )
        elif trade.trade_type == TradeType.SELL:
            self.trade_add_to_sell_events(trade, False)
        elif trade.trade_type == TradeType.SETTLEMENT_SELL:
            # in poloniex settlements sell some asset to get BTC to repay a loan
            self.trade_add_to_sell_events(trade, True)
        elif trade.trade_type == TradeType.SETTLEMENT_BUY:
            # in poloniex settlements you buy some asset with BTC to repay a loan
            # so in essense you sell BTC to repay the loan
            selling_asset = A_BTC
            selling_asset_rate = self.events.base.get_rate_in_profit_currency(
                selling_asset,
                trade.timestamp,
            )
            selling_rate = selling_asset_rate * trade.rate
            fee_in_profit_currency = self.get_fee_in_profit_currency(trade)
            gain_in_profit_currency = selling_rate * trade.amount
            # Since the original trade is a buy of some asset with BTC, then the
            # when we invert the sell, the sold amount of BTC should be the cost
            # (amount*rate) of the original buy
            selling_amount = trade.rate * trade.amount
            self.events.base.add_sell(
                location=trade.location,
                selling_asset=selling_asset,
                selling_amount=selling_amount,
                receiving_asset=None,
                receiving_amount=None,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=fee_in_profit_currency,
                fee_currency=trade.fee_currency,
                fee_amount=trade.fee,
                rate_in_profit_currency=selling_asset_rate,
                timestamp=trade.timestamp,
                loan_settlement=True,
                link=link,
                notes=notes,
            )
        else:
            # Should never happen
            raise AssertionError(f'Unknown trade type "{trade.trade_type}" encountered')

        return 1, prev_time
