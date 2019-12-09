import csv
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import (
    EV_ASSET_MOVE,
    EV_BUY,
    EV_INTEREST_PAYMENT,
    EV_LOAN_SETTLE,
    EV_MARGIN_CLOSE,
    EV_SELL,
    EV_TX_GAS_COST,
    S_EMPTYSTR,
    ZERO,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter, make_sensitive
from rotkehlchen.typing import (
    AssetMovementCategory,
    EmptyStr,
    EventType,
    Fee,
    FilePath,
    Location,
    Timestamp,
)
from rotkehlchen.utils.misc import taxable_gain_for_sell, timestamp_to_date

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FILENAME_TRADES_CSV = 'trades.csv'
FILENAME_LOAN_PROFITS_CSV = 'loan_profits.csv'
FILENAME_ASSET_MOVEMENTS_CSV = 'asset_movements.csv'
FILENAME_GAS_CSV = 'tx_gas_costs.csv'
FILENAME_MARGIN_CSV = 'margin_positions.csv'
FILENAME_LOAN_SETTLEMENTS_CSV = 'loan_settlements.csv'
FILENAME_ALL_CSV = 'all_events.csv'


def _dict_to_csv_file(path: FilePath, dictionary_list: List) -> None:
    """Takes a filepath and a list of dictionaries representing the rows and writes them
    into the file as a CSV"""
    if len(dictionary_list) == 0:
        log.debug('Skipping writting empty CSV for {}'.format(path))
        return

    with open(path, 'w') as f:
        w = csv.DictWriter(f, dictionary_list[0].keys())
        w.writeheader()
        for dic in dictionary_list:
            w.writerow(dic)


class CSVExporter():

    def __init__(
            self,
            profit_currency: Asset,
            user_directory: FilePath,
            create_csv: bool,
    ):
        self.user_directory = user_directory
        self.profit_currency = profit_currency
        self.create_csv = create_csv
        self.all_events: List[Dict[str, Any]] = list()
        self.reset_csv_lists()

    def reset_csv_lists(self) -> None:
        # TODO: Further specify the types here in more detail. Get rid of "Any"
        if self.create_csv:
            self.trades_csv: List[Dict[str, Any]] = list()
            self.loan_profits_csv: List[Dict[str, Any]] = list()
            self.asset_movements_csv: List[Dict[str, Any]] = list()
            self.tx_gas_costs_csv: List[Dict[str, Any]] = list()
            self.margin_positions_csv: List[Dict[str, Any]] = list()
            self.loan_settlements_csv: List[Dict[str, Any]] = list()
            self.all_events_csv: List[Dict[str, Any]] = list()
            self.all_events = list()

    def add_to_allevents(
            self,
            event_type: EventType,
            paid_in_profit_currency: FVal,
            paid_asset: Union[Asset, EmptyStr],
            paid_in_asset: FVal,
            received_asset: Union[Asset, EmptyStr],
            received_in_asset: FVal,
            taxable_received_in_profit_currency: FVal,
            timestamp: Timestamp,
            is_virtual: bool = False,
            taxable_amount: FVal = ZERO,
            taxable_bought_cost: FVal = ZERO,
    ) -> None:
        row = len(self.all_events_csv) + 2
        if event_type == EV_BUY:
            net_profit_or_loss = FVal(0)  # no profit by buying
            net_profit_or_loss_csv = '0'
        elif event_type == EV_SELL:
            if taxable_amount == 0:
                net_profit_or_loss = FVal(0)
            else:
                net_profit_or_loss = taxable_received_in_profit_currency - taxable_bought_cost
            net_profit_or_loss_csv = '=IF(D{}=0,0,K{}-L{})'.format(row, row, row)
        elif event_type in (EV_TX_GAS_COST, EV_ASSET_MOVE, EV_LOAN_SETTLE):
            net_profit_or_loss = paid_in_profit_currency
            net_profit_or_loss_csv = '=-J{}'.format(row)
        elif event_type in (EV_INTEREST_PAYMENT, EV_MARGIN_CLOSE):
            net_profit_or_loss = taxable_received_in_profit_currency
            net_profit_or_loss_csv = '=K{}'.format(row)
        else:
            raise ValueError('Illegal event type "{}" at add_to_allevents'.format(event_type))

        exported_paid_asset = (
            paid_asset if isinstance(paid_asset, str) else paid_asset.identifier
        )
        exported_received_asset = (
            received_asset if isinstance(received_asset, str) else received_asset.identifier
        )
        entry = {
            'type': event_type,
            'paid_in_profit_currency': paid_in_profit_currency,
            'paid_asset': exported_paid_asset,
            'paid_in_asset': paid_in_asset,
            'taxable_amount': taxable_amount,
            'taxable_bought_cost_in_profit_currency': taxable_bought_cost,
            'received_asset': exported_received_asset,
            'taxable_received_in_profit_currency': taxable_received_in_profit_currency,
            'received_in_asset': received_in_asset,
            'net_profit_or_loss': net_profit_or_loss,
            'time': timestamp,
            'is_virtual': is_virtual,
        }
        log.debug('csv event', **make_sensitive(entry))
        self.all_events.append(entry)
        new_entry = entry.copy()
        new_entry['net_profit_or_loss'] = net_profit_or_loss_csv
        new_entry['time'] = timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S')
        new_entry[f'paid_in_{self.profit_currency.identifier}'] = paid_in_profit_currency
        key = f'taxable_received_in_{self.profit_currency.identifier}'
        new_entry[key] = taxable_received_in_profit_currency
        key = f'taxable_bought_cost_in_{self.profit_currency.identifier}'
        new_entry[key] = taxable_bought_cost
        del new_entry['paid_in_profit_currency']
        del new_entry['taxable_received_in_profit_currency']
        del new_entry['taxable_bought_cost_in_profit_currency']
        self.all_events_csv.append(new_entry)

    def add_buy(
            self,
            bought_asset: Asset,
            rate: FVal,
            fee_cost: Fee,
            amount: FVal,
            cost: FVal,
            paid_with_asset: Asset,
            paid_with_asset_rate: FVal,
            timestamp: Timestamp,
            is_virtual: bool,
    ) -> None:
        if not self.create_csv:
            return

        exchange_rate_key = f'exchanged_asset_{self.profit_currency.identifier}_exchange_rate'
        self.trades_csv.append({
            'type': 'buy',
            'asset': bought_asset.identifier,
            'price_in_{}'.format(self.profit_currency.identifier): rate,
            'fee_in_{}'.format(self.profit_currency.identifier): fee_cost,
            'gained_or_invested_{}'.format(self.profit_currency.identifier): cost,
            'amount': amount,
            'taxable_amount': 'not applicable',  # makes no difference for buying
            'exchanged_for': paid_with_asset.identifier,
            exchange_rate_key: paid_with_asset_rate,
            'taxable_bought_cost_in_{}'.format(self.profit_currency.identifier): 'not applicable',
            'taxable_gain_in_{}'.format(self.profit_currency.identifier): FVal(0),
            'taxable_profit_loss_in_{}'.format(self.profit_currency.identifier): FVal(0),
            'time': timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'is_virtual': is_virtual,
        })
        self.add_to_allevents(
            event_type=EV_BUY,
            paid_in_profit_currency=cost,
            paid_asset=self.profit_currency,
            paid_in_asset=cost,
            received_asset=bought_asset,
            received_in_asset=amount,
            taxable_received_in_profit_currency=FVal(0),
            timestamp=timestamp,
            is_virtual=is_virtual,
        )

    def add_sell(
            self,
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
    ) -> None:
        if not self.create_csv:
            return

        processed_receiving_asset: Union[EmptyStr, Asset] = (
            EmptyStr('') if receiving_asset is None else receiving_asset
        )
        exported_receiving_asset = '' if receiving_asset is None else receiving_asset.identifier
        processed_receiving_amount = FVal(0) if not receiving_amount else receiving_amount
        exchange_rate_key = f'exchanged_asset_{self.profit_currency.identifier}_exchange_rate'
        taxable_profit_received = taxable_gain_for_sell(
            taxable_amount=taxable_amount,
            rate_in_profit_currency=rate_in_profit_currency,
            total_fee_in_profit_currency=total_fee_in_profit_currency,
            selling_amount=selling_amount,
        )
        row = len(self.trades_csv) + 2
        taxable_profit_formula = '=IF(G{}=0,0,K{}-J{})'.format(row, row, row)
        self.trades_csv.append({
            'type': 'sell',
            'asset': selling_asset.identifier,
            f'price_in_{self.profit_currency.identifier}': rate_in_profit_currency,
            f'fee_in_{self.profit_currency.identifier}': total_fee_in_profit_currency,
            f'gained_or_invested_{self.profit_currency.identifier}': gain_in_profit_currency,
            'amount': selling_amount,
            'taxable_amount': taxable_amount,
            'exchanged_for': exported_receiving_asset,
            exchange_rate_key: receiving_asset_rate_in_profit_currency,
            f'taxable_bought_cost_in_{self.profit_currency.identifier}': taxable_bought_cost,
            f'taxable_gain_in_{self.profit_currency.identifier}': taxable_profit_received,
            f'taxable_profit_loss_in_{self.profit_currency.identifier}': taxable_profit_formula,
            'time': timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'is_virtual': is_virtual,
        })
        paid_in_profit_currency = ZERO
        self.add_to_allevents(
            event_type=EV_SELL,
            paid_in_profit_currency=paid_in_profit_currency,
            paid_asset=selling_asset,
            paid_in_asset=selling_amount,
            received_asset=processed_receiving_asset,
            received_in_asset=processed_receiving_amount,
            taxable_received_in_profit_currency=taxable_profit_received,
            timestamp=timestamp,
            is_virtual=is_virtual,
            taxable_amount=taxable_amount,
            taxable_bought_cost=taxable_bought_cost,
        )

    def add_loan_settlement(
            self,
            asset: Asset,
            amount: FVal,
            rate_in_profit_currency: FVal,
            total_fee_in_profit_currency: FVal,
            timestamp: Timestamp,
    ) -> None:
        if not self.create_csv:
            return

        row = len(self.loan_settlements_csv) + 2
        loss_formula = '=B{}*C{}+D{}'.format(row, row, row)
        self.loan_settlements_csv.append({
            'asset': asset.identifier,
            'amount': amount,
            f'price_in_{self.profit_currency.identifier}': rate_in_profit_currency,
            f'fee_in_{self.profit_currency.identifier}': total_fee_in_profit_currency,
            f'loss_in_{self.profit_currency.identifier}': loss_formula,
            'time': timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
        })
        paid_in_profit_currency = amount * rate_in_profit_currency + total_fee_in_profit_currency
        self.add_to_allevents(
            event_type=EV_LOAN_SETTLE,
            paid_in_profit_currency=paid_in_profit_currency,
            paid_asset=asset,
            paid_in_asset=amount,
            received_asset=S_EMPTYSTR,
            received_in_asset=FVal(0),
            taxable_received_in_profit_currency=FVal(0),
            timestamp=timestamp,
        )

    def add_loan_profit(
            self,
            gained_asset: Asset,
            gained_amount: FVal,
            gain_in_profit_currency: FVal,
            lent_amount: FVal,
            open_time: Timestamp,
            close_time: Timestamp,
    ) -> None:
        if not self.create_csv:
            return

        self.loan_profits_csv.append({
            'open_time': timestamp_to_date(open_time, formatstr='%d/%m/%Y %H:%M:%S'),
            'close_time': timestamp_to_date(close_time, formatstr='%d/%m/%Y %H:%M:%S'),
            'gained_asset': gained_asset.identifier,
            'gained_amount': gained_amount,
            'lent_amount': lent_amount,
            f'profit_in_{self.profit_currency.identifier}': gain_in_profit_currency,
        })
        self.add_to_allevents(
            event_type=EV_INTEREST_PAYMENT,
            paid_in_profit_currency=FVal(0),
            paid_asset=S_EMPTYSTR,
            paid_in_asset=FVal(0),
            received_asset=gained_asset,
            received_in_asset=gained_amount,
            taxable_received_in_profit_currency=gain_in_profit_currency,
            timestamp=close_time,
        )

    def add_margin_position(
            self,
            margin_notes: str,
            gain_loss_asset: Asset,
            gain_loss_amount: FVal,
            gain_loss_in_profit_currency: FVal,
            timestamp: Timestamp,
    ) -> None:
        if not self.create_csv:
            return

        # Note:  We are not getting the fee info in here but they are not needed
        # in the final CSV export.

        self.margin_positions_csv.append({
            'name': margin_notes,
            'time': timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'gain_loss_asset': gain_loss_asset.identifier,
            'gain_loss_amount': gain_loss_amount,
            f'profit_loss_in_{self.profit_currency.identifier}': gain_loss_in_profit_currency,
        })
        self.add_to_allevents(
            event_type=EV_MARGIN_CLOSE,
            paid_in_profit_currency=FVal(0),
            paid_asset=S_EMPTYSTR,
            paid_in_asset=FVal(0),
            received_asset=gain_loss_asset,
            received_in_asset=gain_loss_amount,
            taxable_received_in_profit_currency=gain_loss_in_profit_currency,
            timestamp=timestamp,
        )

    def add_asset_movement(
            self,
            exchange: Location,
            category: AssetMovementCategory,
            asset: Asset,
            fee: Fee,
            rate: FVal,
            timestamp: Timestamp,
    ) -> None:
        if not self.create_csv:
            return

        self.asset_movements_csv.append({
            'time': timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'exchange': str(exchange),
            'type': str(category),
            'moving_asset': asset.identifier,
            'fee_in_asset': fee,
            f'fee_in_{self.profit_currency.identifier}': fee * rate,
        })
        self.add_to_allevents(
            event_type=EV_ASSET_MOVE,
            paid_in_profit_currency=fee * rate,
            paid_asset=asset,
            paid_in_asset=fee,
            received_asset=S_EMPTYSTR,
            received_in_asset=FVal(0),
            taxable_received_in_profit_currency=FVal(0),
            timestamp=timestamp,
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
            'time': timestamp_to_date(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'transaction_hash': transaction_hash.hex(),
            'eth_burned_as_gas': eth_burned_as_gas,
            f'cost_in_{self.profit_currency.identifier}': eth_burned_as_gas * rate,
        })
        self.add_to_allevents(
            event_type=EV_TX_GAS_COST,
            paid_in_profit_currency=eth_burned_as_gas * rate,
            paid_asset=A_ETH,
            paid_in_asset=eth_burned_as_gas,
            received_asset=S_EMPTYSTR,
            received_in_asset=FVal(0),
            taxable_received_in_profit_currency=FVal(0),
            timestamp=timestamp,
        )

    def create_files(self, dirpath: Path) -> Tuple[bool, str]:
        if not self.create_csv:
            return True, ''

        try:
            if not dirpath.exists():
                os.makedirs(dirpath)

            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_TRADES_CSV)),
                self.trades_csv,
            )
            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_LOAN_PROFITS_CSV)),
                self.loan_profits_csv,
            )
            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_ASSET_MOVEMENTS_CSV)),
                self.asset_movements_csv,
            )
            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_GAS_CSV)),
                self.tx_gas_costs_csv,
            )
            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_MARGIN_CSV)),
                self.margin_positions_csv,
            )
            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_LOAN_SETTLEMENTS_CSV)),
                self.loan_settlements_csv,
            )
            _dict_to_csv_file(
                FilePath(os.path.join(dirpath, FILENAME_ALL_CSV)),
                self.all_events_csv,
            )
        except (PermissionError, OSError) as e:
            return False, str(e)

        return True, ''
