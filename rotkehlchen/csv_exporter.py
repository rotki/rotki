import csv
import json
import logging
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from zipfile import ZipFile

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures import DefiEvent
from rotkehlchen.accounting.typing import NamedJson, SchemaEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import (
    EV_ASSET_MOVE,
    EV_BUY,
    EV_DEFI,
    EV_INTEREST_PAYMENT,
    EV_LEDGER_ACTION,
    EV_LOAN_SETTLE,
    EV_MARGIN_CLOSE,
    EV_SELL,
    EV_TX_GAS_COST,
    ZERO,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache_handler import DBAccountingReports
from rotkehlchen.errors import DeserializationError, InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    AssetAmount,
    AssetMovementCategory,
    EventType,
    Fee,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import taxable_gain_for_sell, timestamp_to_date
from rotkehlchen.utils.version_check import check_if_version_up_to_date

if TYPE_CHECKING:
    from rotkehlchen.accounting.cost_basis import CostBasisInfo
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.settings import DBSettings

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FILENAME_TRADES_CSV = 'trades.csv'
FILENAME_LOAN_PROFITS_CSV = 'loan_profits.csv'
FILENAME_ASSET_MOVEMENTS_CSV = 'asset_movements.csv'
FILENAME_GAS_CSV = 'tx_gas_costs.csv'
FILENAME_MARGIN_CSV = 'margin_positions.csv'
FILENAME_LOAN_SETTLEMENTS_CSV = 'loan_settlements.csv'
FILENAME_DEFI_EVENTS_CSV = 'defi_events.csv'
FILENAME_LEDGER_ACTIONS_CSV = 'ledger_actions.csv'
FILENAME_ALL_CSV = 'all_events.csv'
ETH_EXPLORER = 'https://etherscan.io/tx/'

ACCOUNTING_SETTINGS = (
    'include_crypto2crypto',
    'taxfree_after_period',
    'include_gas_costs',
    'account_for_assets_movements',
    'calculate_past_cost_basis',
)


class CSVWriteError(Exception):
    pass


def _dict_to_csv_file(path: Path, dictionary_list: List) -> None:
    """Takes a filepath and a list of dictionaries representing the rows and writes them
    into the file as a CSV

    May raise:
    - CSVWriteError if DictWriter.writerow() tried to write a dict contains
    fields not in fieldnames
    """
    if len(dictionary_list) == 0:
        log.debug('Skipping writting empty CSV for {}'.format(path))
        return

    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=dictionary_list[0].keys())
        w.writeheader()
        try:
            for dic in dictionary_list:
                w.writerow(dic)
        except ValueError as e:
            raise CSVWriteError(f'Failed to write {path} CSV due to {str(e)}') from e


class CSVExporter():

    def __init__(
            self,
            database: 'DBHandler',
            user_directory: Path,
            create_csv: bool,
    ):
        self.user_directory = user_directory
        self.database = database
        self.create_csv = create_csv
        self.all_events: List[Dict[str, Any]] = []
        self.report_id: Optional[int] = None
        self.cached: bool = False
        self.reset()

        # get setting for prefered eth explorer
        user_settings = self.database.get_settings()
        try:
            frontend_settings = json.loads(user_settings.frontend_settings)
            if (
                'explorers' in frontend_settings and
                'ETH' in frontend_settings['explorers'] and
                'transaction' in frontend_settings['explorers']['ETH']
            ):
                self.eth_explorer = frontend_settings['explorers']['ETH']['transaction']
            else:
                self.eth_explorer = ETH_EXPLORER
        except (json.decoder.JSONDecodeError, KeyError):
            self.eth_explorer = ETH_EXPLORER

    def reset(self) -> None:
        """Resets the CSVExporter and prepares it for a new profit/loss run"""
        # TODO: Further specify the types here in more detail. Get rid of "Any"
        self.profit_currency = self.database.get_main_currency()
        db_settings = self.database.get_settings()
        self.dateformat = db_settings.date_display_format
        self.datelocaltime = db_settings.display_date_in_localtime
        self.should_export_formulas = db_settings.pnl_csv_with_formulas
        self.should_have_summary = db_settings.pnl_csv_have_summary
        if self.create_csv:
            self.trades_csv: List[Dict[str, Any]] = []
            self.loan_profits_csv: List[Dict[str, Any]] = []
            self.asset_movements_csv: List[Dict[str, Any]] = []
            self.tx_gas_costs_csv: List[Dict[str, Any]] = []
            self.margin_positions_csv: List[Dict[str, Any]] = []
            self.loan_settlements_csv: List[Dict[str, Any]] = []
            self.defi_events_csv: List[Dict[str, Any]] = []
            self.ledger_actions_csv: List[Dict[str, Any]] = []
            self.all_events_csv: List[Dict[str, Any]] = []
            self.all_events = []
            self.report_id = None
            self.cached = False

    def create_pnlreport_in_db(
            self,
            first_processed_timestamp: Timestamp,
            start_ts: Timestamp,
            end_ts: Timestamp,
            profit_currency: Asset,
            settings: 'DBSettings',
    ) -> int:
        """Creates a new report in the DB and sets it as current for the csv exporter"""
        dbreports = DBAccountingReports(self.database)
        self.report_id = dbreports.add_report(
            first_processed_timestamp=first_processed_timestamp,
            start_ts=start_ts,
            end_ts=end_ts,
            profit_currency=profit_currency,
            settings=settings,
        )
        return self.report_id

    def timestamp_to_date(self, timestamp: Timestamp) -> str:
        return timestamp_to_date(
            timestamp,
            formatstr=self.dateformat,
            treat_as_local=self.datelocaltime,
        )

    def _add_if_formula(
            self,
            condition: str,
            if_true: str,
            if_false: str,
            actual_value: FVal,
    ) -> str:
        if self.should_export_formulas is False:
            return str(actual_value)

        return f'=IF({condition};{if_true};{if_false})'

    def _add_sumif_formula(
            self,
            check_range: str,
            condition: str,
            sum_range: str,
            actual_value: FVal,
    ) -> str:
        if self.should_export_formulas is False:
            return str(actual_value)

        return f'=SUMIF({check_range};{condition};{sum_range})'

    def _add_equals_formula(self, expression: str, actual_value: FVal) -> str:
        if self.should_export_formulas is False:
            return str(actual_value)

        return f'={expression}'

    def _add_settings_lines(self, db_settings: 'DBSettings', template: Dict[str, Any]) -> None:
        for setting in ACCOUNTING_SETTINGS:
            entry = template.copy()
            entry['received_in_asset'] = setting
            entry['net_profit_or_loss'] = str(getattr(db_settings, setting))
            self.all_events_csv.append(entry)

    def maybe_add_summary(
            self,
            ledger_actions_profit_loss: FVal,
            defi_profit_loss: FVal,
            loan_profit: FVal,
            margin_position_profit_loss: FVal,
            settlement_losses: FVal,
            ethereum_transaction_gas_costs: FVal,
            asset_movement_fees: FVal,
            taxable_trade_profit_loss: FVal,
            total_taxable_profit_loss: FVal,
    ) -> None:
        """Depending on given settings, adds a few summary lines at the end of
        the all events PnL report"""
        if self.should_have_summary is False:
            return

        length = len(self.all_events_csv) + 1
        template: Dict[str, Any] = {
            'type': '',
            'location': '',
            'paid_asset': '',
            'paid_in_asset': '',
            'taxable_amount': '',
            'received_asset': '',
            'received_in_asset': '',
            'net_profit_or_loss': '',
            'time': '',
            'is_virtual': '',
            f'paid_in_{self.profit_currency.symbol}': '',
            f'taxable_received_in_{self.profit_currency.symbol}': '',
            f'taxable_bought_cost_in_{self.profit_currency.symbol}': '',
            'cost_basis': '',
            f'total_bought_cost_in_{self.profit_currency.symbol}': '',
            f'total_received_in_{self.profit_currency.symbol}': '',
        }
        self.all_events_csv.append(template)  # separate with 2 new lines
        self.all_events_csv.append(template)

        entry = template.copy()
        entry['received_in_asset'] = 'LEDGER ACTIONS PROFIT/LOSS'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_LEDGER_ACTION}"',
            sum_range=f'H2:H{length}',
            actual_value=ledger_actions_profit_loss,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'DEFI PROFIT/LOSS'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_DEFI}"',
            sum_range=f'H2:H{length}',
            actual_value=defi_profit_loss,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'LOAN PROFIT/LOSS'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_INTEREST_PAYMENT}"',
            sum_range=f'H2:H{length}',
            actual_value=loan_profit,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'MARGIN POSITIONS PROFIT/LOSS'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_MARGIN_CLOSE}"',
            sum_range=f'H2:H{length}',
            actual_value=margin_position_profit_loss,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'SETTLEMENT LOSS'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_LOAN_SETTLE}"',
            sum_range=f'H2:H{length}',
            actual_value=settlement_losses,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'ETHEREUM TX GAS COST'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_TX_GAS_COST}"',
            sum_range=f'H2:H{length}',
            actual_value=ethereum_transaction_gas_costs,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'ASSET MOVEMENT FEES'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_ASSET_MOVE}"',
            sum_range=f'H2:H{length}',
            actual_value=asset_movement_fees,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'TAXABLE TRADE PROFIT/LOSS'
        entry['net_profit_or_loss'] = self._add_sumif_formula(
            check_range=f'A2:A{length}',
            condition=f'"{EV_SELL}"',
            sum_range=f'H2:H{length}',
            actual_value=taxable_trade_profit_loss,
        )
        self.all_events_csv.append(entry)

        entry = template.copy()
        entry['received_in_asset'] = 'TOTAL TAXABLE PROFIT/LOSS'
        start = length + 3
        entry['net_profit_or_loss'] = self._add_equals_formula(
            expression=f'H{start}+H{start + 1}+H{start + 2}+H{start + 3}+H{start + 4}+H{start + 5}+H{start + 6}+H{start + 7}',  # noqa: E501
            actual_value=total_taxable_profit_loss,
        )
        self.all_events_csv.append(entry)

        self.all_events_csv.append(template)  # separate with 2 new lines
        self.all_events_csv.append(template)

        version_result = check_if_version_up_to_date()
        entry = template.copy()
        entry['received_in_asset'] = 'rotki version'
        entry['net_profit_or_loss'] = version_result.our_version
        self.all_events_csv.append(entry)

        db_settings = self.database.get_settings()
        self._add_settings_lines(db_settings, template)

    def add_to_allevents(
            self,
            event_type: EventType,
            location: Location,
            paid_in_profit_currency: FVal,
            paid_asset: Optional[Asset],
            paid_in_asset: FVal,
            received_asset: Optional[Asset],
            received_in_asset: FVal,
            taxable_received_in_profit_currency: FVal,
            total_received_in_profit_currency: FVal,
            timestamp: Timestamp,
            is_virtual: bool = False,
            taxable_amount: FVal = ZERO,
            taxable_bought_cost: FVal = ZERO,
            total_bought_cost: FVal = ZERO,
            cost_basis_info: Optional['CostBasisInfo'] = None,
            link: Optional[str] = '',
            notes: Optional[str] = '',
    ) -> None:
        row = len(self.all_events_csv) + 2
        if event_type == EV_BUY:
            net_profit_or_loss = ZERO  # no profit by buying
            net_profit_or_loss_csv = '0'
        elif event_type == EV_SELL:
            if taxable_amount == 0:
                net_profit_or_loss = ZERO
            else:
                net_profit_or_loss = taxable_received_in_profit_currency - taxable_bought_cost

            net_profit_or_loss_csv = self._add_if_formula(
                condition=f'E{row}=0',
                if_true='0',
                if_false=f'L{row}-M{row}',
                actual_value=net_profit_or_loss,
            )
        elif event_type in (EV_TX_GAS_COST, EV_ASSET_MOVE, EV_LOAN_SETTLE):
            net_profit_or_loss = -paid_in_profit_currency
            net_profit_or_loss_csv = self._add_equals_formula(
                expression=f'-K{row}',
                actual_value=net_profit_or_loss,
            )
        elif event_type == EV_INTEREST_PAYMENT:
            net_profit_or_loss = taxable_received_in_profit_currency
            net_profit_or_loss_csv = self._add_equals_formula(
                expression=f'L{row}',
                actual_value=net_profit_or_loss,
            )
        elif event_type in (EV_MARGIN_CLOSE, EV_DEFI, EV_LEDGER_ACTION):
            if total_received_in_profit_currency > ZERO:
                net_profit_or_loss = total_received_in_profit_currency
            else:
                net_profit_or_loss = -paid_in_profit_currency

            net_profit_or_loss_csv = self._add_if_formula(
                condition=f'P{row}=0',  # total_received_in_profit_currency is 0
                if_true=f'-K{row}',  # then -paid_in_profit_currency
                if_false=f'P{row}',  # else use total_received_in_profit_currency
                actual_value=net_profit_or_loss,
            )
        else:
            raise ValueError('Illegal event type "{}" at add_to_allevents'.format(event_type))

        entry: Dict[str, Any] = {
            'type': event_type,
            'location': str(location),
            'paid_in_profit_currency': paid_in_profit_currency,
            'paid_asset': paid_asset.identifier if paid_asset else '',
            'paid_in_asset': paid_in_asset,
            'taxable_amount': taxable_amount,
            'taxable_bought_cost_in_profit_currency': taxable_bought_cost,
            'received_asset': received_asset.identifier if received_asset else '',
            'taxable_received_in_profit_currency': taxable_received_in_profit_currency,
            'received_in_asset': received_in_asset,
            'net_profit_or_loss': net_profit_or_loss,
            'time': timestamp,
            'cost_basis': cost_basis_info.serialize() if cost_basis_info else None,
            'is_virtual': is_virtual,
            'link': link,
            'notes': notes,
        }
        log.debug('csv event', **entry)
        self.all_events.append(entry)
        if self.cached is False:
            dbpnl = DBAccountingReports(self.database)
            schema_event_type = SchemaEventType.ACCOUNTING_EVENT
            event = NamedJson.deserialize(
                event_type=schema_event_type,
                data=entry,
            )
            assert self.report_id is not None, 'got into add_to_all_events() with a null report_id'
            try:
                dbpnl.add_report_data(self.report_id, timestamp, event)
            except (DeserializationError, InputError) as e:
                log.error(str(e))

        new_entry = entry.copy()
        # deleting and read link and notes for them to be at the end
        del new_entry['link']
        del new_entry['notes']
        # for CSV use the str(asset) and not pure identifier
        new_entry['paid_asset'] = str(paid_asset) if paid_asset else ''
        new_entry['received_asset'] = str(received_asset) if received_asset else ''
        new_entry['net_profit_or_loss'] = net_profit_or_loss_csv
        new_entry['time'] = self.timestamp_to_date(timestamp)
        new_entry[f'paid_in_{self.profit_currency.symbol}'] = paid_in_profit_currency
        key = f'taxable_received_in_{self.profit_currency.symbol}'
        new_entry[key] = taxable_received_in_profit_currency
        key = f'taxable_bought_cost_in_{self.profit_currency.symbol}'
        new_entry[key] = taxable_bought_cost
        del new_entry['cost_basis']  # deleting and re-adding is for appending it to end of dict
        new_entry['cost_basis'] = cost_basis_info.to_string(self.timestamp_to_date) if cost_basis_info else ''  # noqa: E501
        key = f'total_bought_cost_in_{self.profit_currency.symbol}'
        new_entry[key] = total_bought_cost
        key = f'total_received_in_{self.profit_currency.symbol}'
        new_entry[key] = total_received_in_profit_currency
        del new_entry['paid_in_profit_currency']
        del new_entry['taxable_received_in_profit_currency']
        del new_entry['taxable_bought_cost_in_profit_currency']
        new_entry['link'] = link
        new_entry['notes'] = notes
        self.all_events_csv.append(new_entry)

    def add_buy(
            self,
            location: Location,
            bought_asset: Asset,
            rate_in_profit_currency: FVal,
            fee_cost: Fee,
            amount: FVal,
            cost_in_profit_currency: FVal,
            paid_with_asset: Asset,
            paid_with_asset_amount: FVal,
            paid_with_asset_rate: FVal,
            timestamp: Timestamp,
            is_virtual: bool,
            link: Optional[str],
            notes: Optional[str],
    ) -> None:
        if not self.create_csv:
            return

        exchange_rate_key = f'exchanged_asset_{self.profit_currency.symbol}_exchange_rate'
        self.trades_csv.append({
            'type': 'buy',
            'location': str(location),
            'asset': str(bought_asset),
            'price_in_{}'.format(self.profit_currency.symbol): rate_in_profit_currency,
            'fee_in_{}'.format(self.profit_currency.symbol): fee_cost,
            'gained_or_invested_{}'.format(self.profit_currency.symbol): cost_in_profit_currency,  # noqa: E501
            'amount': amount,
            'taxable_amount': 'N/A',  # makes no difference for buying
            'exchanged_for': str(paid_with_asset),
            exchange_rate_key: paid_with_asset_rate,
            'taxable_bought_cost_in_{}'.format(self.profit_currency.symbol): 'N/A',
            'taxable_gain_in_{}'.format(self.profit_currency.symbol): ZERO,
            'taxable_profit_loss_in_{}'.format(self.profit_currency.symbol): ZERO,
            'time': self.timestamp_to_date(timestamp),
            'cost_basis': 'N/A',
            'is_virtual': is_virtual,
            f'total_bought_cost_in_{self.profit_currency.symbol}': ZERO,
            'link': link,
            'notes': notes,
        })
        self.add_to_allevents(
            event_type=EV_BUY,
            location=location,
            paid_in_profit_currency=cost_in_profit_currency,
            paid_asset=paid_with_asset,
            paid_in_asset=paid_with_asset_amount,
            received_asset=bought_asset,
            received_in_asset=amount,
            taxable_received_in_profit_currency=ZERO,
            total_received_in_profit_currency=ZERO,
            timestamp=timestamp,
            is_virtual=is_virtual,
            link=link,
            notes=notes,
        )

    def add_sell(
            self,
            location: Location,
            selling_asset: Asset,
            rate_in_profit_currency: FVal,
            total_fee_in_profit_currency: Fee,
            gain_in_profit_currency: FVal,
            selling_amount: FVal,
            receiving_asset: Optional[Asset],
            receiving_amount: Optional[FVal],
            receiving_asset_rate_in_profit_currency: FVal,
            taxable_amount: FVal,
            taxable_bought_cost: FVal,
            timestamp: Timestamp,
            is_virtual: bool,
            cost_basis_info: 'CostBasisInfo',
            total_bought_cost: FVal,
            link: Optional[str],
            notes: Optional[str],
    ) -> None:
        if not self.create_csv:
            return

        exported_receiving_asset = '' if receiving_asset is None else str(receiving_asset)
        processed_receiving_amount = ZERO if not receiving_amount else receiving_amount
        exchange_rate_key = f'exchanged_asset_{self.profit_currency.symbol}_exchange_rate'
        taxable_profit_received = taxable_gain_for_sell(
            taxable_amount=taxable_amount,
            rate_in_profit_currency=rate_in_profit_currency,
            total_fee_in_profit_currency=total_fee_in_profit_currency,
            selling_amount=selling_amount,
        )
        row = len(self.trades_csv) + 2
        taxable_profit_csv = self._add_if_formula(
            condition=f'H{row}=0',
            if_true='0',
            if_false=f'L{row}-K{row}',
            actual_value=taxable_profit_received,
        )
        self.trades_csv.append({
            'type': 'sell',
            'location': str(location),
            'asset': str(selling_asset),
            f'price_in_{self.profit_currency.symbol}': rate_in_profit_currency,
            f'fee_in_{self.profit_currency.symbol}': total_fee_in_profit_currency,
            f'gained_or_invested_{self.profit_currency.symbol}': gain_in_profit_currency,
            'amount': selling_amount,
            'taxable_amount': taxable_amount,
            'exchanged_for': exported_receiving_asset,
            exchange_rate_key: receiving_asset_rate_in_profit_currency,
            f'taxable_bought_cost_in_{self.profit_currency.symbol}': taxable_bought_cost,
            f'taxable_gain_in_{self.profit_currency.symbol}': taxable_profit_received,
            f'taxable_profit_loss_in_{self.profit_currency.symbol}': taxable_profit_csv,
            'time': self.timestamp_to_date(timestamp),
            'cost_basis': cost_basis_info.to_string(self.timestamp_to_date),
            'is_virtual': is_virtual,
            f'total_bought_cost_in_{self.profit_currency.symbol}': total_bought_cost,
            'link': link,
            'notes': notes,
        })
        paid_in_profit_currency = ZERO
        self.add_to_allevents(
            event_type=EV_SELL,
            location=location,
            paid_in_profit_currency=paid_in_profit_currency,
            paid_asset=selling_asset,
            paid_in_asset=selling_amount,
            received_asset=receiving_asset,
            received_in_asset=processed_receiving_amount,
            taxable_received_in_profit_currency=taxable_profit_received,
            total_received_in_profit_currency=gain_in_profit_currency,
            timestamp=timestamp,
            is_virtual=is_virtual,
            taxable_amount=taxable_amount,
            taxable_bought_cost=taxable_bought_cost,
            total_bought_cost=total_bought_cost,
            cost_basis_info=cost_basis_info,
            link=link,
            notes=notes,
        )

    def add_loan_settlement(
            self,
            location: Location,
            asset: Asset,
            amount: FVal,
            rate_in_profit_currency: FVal,
            total_fee_in_profit_currency: FVal,
            timestamp: Timestamp,
            cost_basis_info: 'CostBasisInfo',
            link: Optional[str],
            notes: Optional[str],
    ) -> None:
        if not self.create_csv:
            return

        paid_in_profit_currency = amount * rate_in_profit_currency + total_fee_in_profit_currency
        row = len(self.loan_settlements_csv) + 2
        loss_csv = self._add_equals_formula(
            expression=f'C{row}*D{row}+E{row}',
            actual_value=paid_in_profit_currency,
        )
        self.loan_settlements_csv.append({
            'asset': str(asset),
            'location': str(location),
            'amount': amount,
            f'price_in_{self.profit_currency.symbol}': rate_in_profit_currency,
            f'fee_in_{self.profit_currency.symbol}': total_fee_in_profit_currency,
            f'loss_in_{self.profit_currency.symbol}': loss_csv,
            'cost_basis': cost_basis_info.to_string(self.timestamp_to_date),
            'time': self.timestamp_to_date(timestamp),
            'link': link,
            'notes': notes,
        })
        self.add_to_allevents(
            event_type=EV_LOAN_SETTLE,
            location=location,
            paid_in_profit_currency=paid_in_profit_currency,
            paid_asset=asset,
            paid_in_asset=amount,
            received_asset=None,
            received_in_asset=ZERO,
            taxable_received_in_profit_currency=ZERO,
            total_received_in_profit_currency=ZERO,
            timestamp=timestamp,
            cost_basis_info=cost_basis_info,
            link=link,
            notes=notes,
        )

    def add_loan_profit(
            self,
            location: Location,
            gained_asset: Asset,
            gained_amount: FVal,
            gain_in_profit_currency: FVal,
            lent_amount: FVal,
            open_time: Timestamp,
            close_time: Timestamp,
            link: Optional[str],
            notes: Optional[str],
    ) -> None:
        if not self.create_csv:
            return

        self.loan_profits_csv.append({
            'location': str(location),
            'open_time': self.timestamp_to_date(open_time),
            'close_time': self.timestamp_to_date(close_time),
            'gained_asset': str(gained_asset),
            'gained_amount': gained_amount,
            'lent_amount': lent_amount,
            f'profit_in_{self.profit_currency.symbol}': gain_in_profit_currency,
            'link': link,
            'notes': notes,
        })
        self.add_to_allevents(
            location=location,
            event_type=EV_INTEREST_PAYMENT,
            paid_in_profit_currency=ZERO,
            paid_asset=None,
            paid_in_asset=ZERO,
            received_asset=gained_asset,
            received_in_asset=gained_amount,
            taxable_received_in_profit_currency=gain_in_profit_currency,
            total_received_in_profit_currency=gain_in_profit_currency,
            timestamp=close_time,
            link=link,
            notes=notes,
        )

    def add_margin_position(
            self,
            location: Location,
            margin_notes: str,
            gain_loss_asset: Asset,
            gain_loss_amount: FVal,
            gain_loss_in_profit_currency: FVal,
            timestamp: Timestamp,
            link: str,
            notes: str,
    ) -> None:
        if not self.create_csv:
            return

        # Note:  We are not getting the fee info in here but they are not needed
        # in the final CSV export.

        self.margin_positions_csv.append({
            'name': margin_notes,
            'location': str(location),
            'time': self.timestamp_to_date(timestamp),
            'gain_loss_asset': str(gain_loss_asset),
            'gain_loss_amount': gain_loss_amount,
            f'profit_loss_in_{self.profit_currency.symbol}': gain_loss_in_profit_currency,
            'link': link,
            'notes': notes,
        })

        paid_in_profit_currency = ZERO
        received_in_profit_currency = ZERO
        paid_in_asset = ZERO
        received_in_asset = ZERO
        if gain_loss_amount >= ZERO:
            received_in_profit_currency = gain_loss_in_profit_currency
            received_in_asset = gain_loss_amount
        else:
            paid_in_profit_currency = -gain_loss_in_profit_currency
            paid_in_asset = -gain_loss_amount

        self.add_to_allevents(
            event_type=EV_MARGIN_CLOSE,
            location=location,
            paid_in_profit_currency=paid_in_profit_currency,
            paid_asset=None,
            paid_in_asset=paid_in_asset,
            received_asset=gain_loss_asset,
            received_in_asset=received_in_asset,
            taxable_received_in_profit_currency=received_in_profit_currency,
            total_received_in_profit_currency=received_in_profit_currency,
            timestamp=timestamp,
            link=link,
            notes=notes,
        )

    def add_asset_movement(
            self,
            exchange: Location,
            category: AssetMovementCategory,
            asset: Asset,
            fee: Fee,
            rate: FVal,
            timestamp: Timestamp,
            link: str,
    ) -> None:
        if not self.create_csv:
            return

        self.asset_movements_csv.append({
            'time': self.timestamp_to_date(timestamp),
            'exchange': str(exchange),
            'type': str(category),
            'moving_asset': str(asset),
            'fee_in_asset': fee,
            f'fee_in_{self.profit_currency.symbol}': fee * rate,
            'link': link,
            'notes': '',
        })
        self.add_to_allevents(
            event_type=EV_ASSET_MOVE,
            location=exchange,
            paid_in_profit_currency=fee * rate,
            paid_asset=asset,
            paid_in_asset=fee,
            received_asset=None,
            received_in_asset=ZERO,
            taxable_received_in_profit_currency=ZERO,
            total_received_in_profit_currency=ZERO,
            timestamp=timestamp,
            link=link,
            notes='',
        )

    def add_tx_gas_cost(
            self,
            transaction_hash: bytes,
            eth_burned_as_gas: FVal,
            rate: FVal,
            timestamp: Timestamp,
    ) -> None:
        if not self.create_csv:
            return

        self.tx_gas_costs_csv.append({
            'time': self.timestamp_to_date(timestamp),
            'transaction_hash': transaction_hash.hex(),
            'eth_burned_as_gas': eth_burned_as_gas,
            f'cost_in_{self.profit_currency.symbol}': eth_burned_as_gas * rate,
        })
        self.add_to_allevents(
            location=Location.BLOCKCHAIN,
            event_type=EV_TX_GAS_COST,
            paid_in_profit_currency=eth_burned_as_gas * rate,
            paid_asset=A_ETH,
            paid_in_asset=eth_burned_as_gas,
            received_asset=None,
            received_in_asset=ZERO,
            taxable_received_in_profit_currency=ZERO,
            total_received_in_profit_currency=ZERO,
            timestamp=timestamp,
            link='',
            notes='',
        )

    def add_defi_event(
            self,
            event: DefiEvent,
            profit_loss_in_profit_currency_list: List[FVal],
    ) -> None:
        if not self.create_csv:
            return

        profit_loss_sum = FVal(sum(profit_loss_in_profit_currency_list))
        if event.tx_hash:
            link = f'{self.eth_explorer}{event.tx_hash}'
        else:
            link = ''
        self.defi_events_csv.append({
            'time': self.timestamp_to_date(event.timestamp),
            'type': str(event.event_type),
            'got_asset': str(event.got_asset) if event.got_asset else '',
            'got_amount': str(event.got_balance.amount) if event.got_balance else '',
            'spent_asset': str(event.spent_asset) if event.spent_asset else '',
            'spent_amount': str(event.spent_balance.amount) if event.spent_balance else '',
            f'profit_loss_in_{self.profit_currency.symbol}': profit_loss_sum,
            'tx_hash': event.tx_hash if event.tx_hash else '',
            'description': event.to_string(timestamp_converter=self.timestamp_to_date),
            'link': link,
            'notes': '',
        })

        paid_asset: Optional[Asset]
        received_asset: Optional[Asset]
        if event.pnl is None:
            return  # don't pollute all events csv with entries that are not useful

        for idx, entry in enumerate(event.pnl):
            if entry.balance.amount > ZERO:
                paid_in_profit_currency = ZERO
                paid_in_asset = ZERO
                paid_asset = None
                received_asset = entry.asset
                received_in_asset = entry.balance.amount
                # The index should be the same as the precalculated profit_currency list amounts
                received_in_profit_currency = profit_loss_in_profit_currency_list[idx]
            else:  # pnl is a loss
                # The index should be the same as the precalculated profit_currency list amounts
                paid_in_profit_currency = profit_loss_in_profit_currency_list[idx]
                paid_in_asset = entry.balance.amount
                paid_asset = entry.asset
                received_asset = None
                received_in_asset = ZERO
                received_in_profit_currency = ZERO

            self.add_to_allevents(
                event_type=EV_DEFI,
                location=Location.BLOCKCHAIN,
                paid_in_profit_currency=paid_in_profit_currency,
                paid_asset=paid_asset,
                paid_in_asset=paid_in_asset,
                received_asset=received_asset,
                received_in_asset=received_in_asset,
                taxable_received_in_profit_currency=received_in_profit_currency,
                total_received_in_profit_currency=received_in_profit_currency,
                timestamp=event.timestamp,
                link=link,
                notes='',
            )

    def add_ledger_action(
            self,
            action: LedgerAction,
            profit_loss_in_profit_currency: FVal,
    ) -> None:
        if not self.create_csv:
            return

        self.ledger_actions_csv.append({
            'time': self.timestamp_to_date(action.timestamp),
            'type': str(action.action_type),
            'location': str(action.location),
            'asset': str(action.asset),
            'amount': str(action.amount),
            f'profit_loss_in_{self.profit_currency.symbol}': profit_loss_in_profit_currency,
        })

        paid_asset: Optional[Asset]
        received_asset: Optional[Asset]
        if action.is_profitable():
            paid_in_profit_currency = ZERO
            paid_in_asset = ZERO
            paid_asset = None
            received_asset = action.asset
            received_in_asset = action.amount
            received_in_profit_currency = profit_loss_in_profit_currency
        else:
            paid_in_profit_currency = profit_loss_in_profit_currency
            paid_in_asset = action.amount
            paid_asset = action.asset
            received_asset = None
            received_in_asset = AssetAmount(ZERO)
            received_in_profit_currency = ZERO

        self.add_to_allevents(
            event_type=EV_LEDGER_ACTION,
            location=action.location,
            paid_in_profit_currency=paid_in_profit_currency,
            paid_asset=paid_asset,
            paid_in_asset=paid_in_asset,
            received_asset=received_asset,
            received_in_asset=received_in_asset,
            taxable_received_in_profit_currency=received_in_profit_currency,
            total_received_in_profit_currency=received_in_profit_currency,
            timestamp=action.timestamp,
            link=action.link,
            notes=action.notes,
        )

    def create_files(self, dirpath: Path) -> Tuple[bool, str]:
        if not self.create_csv:
            return True, ''

        try:
            dirpath.mkdir(parents=True, exist_ok=True)
            _dict_to_csv_file(
                dirpath / FILENAME_TRADES_CSV,
                self.trades_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_LOAN_PROFITS_CSV,
                self.loan_profits_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_ASSET_MOVEMENTS_CSV,
                self.asset_movements_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_GAS_CSV,
                self.tx_gas_costs_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_MARGIN_CSV,
                self.margin_positions_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_LOAN_SETTLEMENTS_CSV,
                self.loan_settlements_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_DEFI_EVENTS_CSV,
                self.defi_events_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_LEDGER_ACTIONS_CSV,
                self.ledger_actions_csv,
            )
            _dict_to_csv_file(
                dirpath / FILENAME_ALL_CSV,
                self.all_events_csv,
            )
        except (CSVWriteError, PermissionError) as e:
            return False, str(e)

        return True, ''

    def create_zip(self) -> Optional[str]:
        if not self.create_csv:
            return None

        # TODO: Find a way to properly delete the directory after send is complete
        dirpath = Path(mkdtemp())
        success, _ = self.create_files(dirpath)
        if not success:
            return None

        files: List[Tuple[Path, str]] = [
            (dirpath / FILENAME_TRADES_CSV, FILENAME_TRADES_CSV),
            (dirpath / FILENAME_LOAN_PROFITS_CSV, FILENAME_LOAN_PROFITS_CSV),
            (dirpath / FILENAME_ASSET_MOVEMENTS_CSV, FILENAME_ASSET_MOVEMENTS_CSV),
            (dirpath / FILENAME_GAS_CSV, FILENAME_GAS_CSV),
            (dirpath / FILENAME_MARGIN_CSV, FILENAME_MARGIN_CSV),
            (dirpath / FILENAME_LOAN_SETTLEMENTS_CSV, FILENAME_LOAN_SETTLEMENTS_CSV),
            (dirpath / FILENAME_DEFI_EVENTS_CSV, FILENAME_DEFI_EVENTS_CSV),
            (dirpath / FILENAME_LEDGER_ACTIONS_CSV, FILENAME_LEDGER_ACTIONS_CSV),
            (dirpath / FILENAME_ALL_CSV, FILENAME_ALL_CSV),
        ]

        with ZipFile(dirpath / 'csv.zip', 'w') as csv_zip:
            for path, filename in files:
                if not path.exists():
                    continue

                csv_zip.write(path, filename)
                path.unlink()

        return csv_zip.filename
