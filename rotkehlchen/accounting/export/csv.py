import json
import logging
import os
from collections.abc import Collection
from csv import DictWriter
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any, Literal
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.pnl import PnlTotals
from rotkehlchen.accounting.structures.processed_event import AccountingEventExportType
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    EVM_EVMLIKE_LOCATIONS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    CostBasisMethod,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FILENAME_ALL_CSV = 'all_events.csv'
FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV = 'skipped_external_events.csv'
ETHERSCAN_EXPLORER_TX_URL = 'https://{base_url}/tx/'

ACCOUNTING_SETTINGS = (
    'include_crypto2crypto',
    'taxfree_after_period',
    'include_gas_costs',
    'calculate_past_cost_basis',
    'cost_basis_method',
)

CSV_INDEX_OFFSET = 2  # skip title row and since counting starts from 1


class CSVWriteError(Exception):
    pass


def dict_to_csv_file(
        path: Path,
        dictionary_list: list,
        csv_delimiter: str,
        headers: Collection | None = None,
) -> None:
    """Takes a filepath and a list of dictionaries representing the rows and writes them
    into the file as a CSV

    May raise:
    - CSVWriteError if DictWriter.writerow() tried to write a dict contains
    fields not in fieldnames
    """
    if len(dictionary_list) == 0:
        log.debug(f'Skipping writing empty CSV for {path}')
        return

    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = DictWriter(f, fieldnames=dictionary_list[0].keys() if headers is None else headers, delimiter=csv_delimiter)  # noqa: E501
        w.writeheader()
        try:
            for dic in dictionary_list:
                w.writerow(dic)
        except ValueError as e:
            raise CSVWriteError(f'Failed to write {path} CSV due to {e!s}') from e

    os.utime(path)


class CSVExporter(CustomizableDateMixin):

    def __init__(
            self,
            database: 'DBHandler',
    ):
        super().__init__(database=database)
        self.reset(start_ts=Timestamp(0), end_ts=Timestamp(0))

    def reset(self, start_ts: Timestamp, end_ts: Timestamp) -> None:
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.transaction_explorers: dict[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, str] = {
            SupportedBlockchain.ETHEREUM: ETHERSCAN_EXPLORER_TX_URL.format(base_url='etherscan.io'),  # noqa: E501
            SupportedBlockchain.OPTIMISM: ETHERSCAN_EXPLORER_TX_URL.format(base_url='optimistic.etherscan.io'),  # noqa: E501
            SupportedBlockchain.POLYGON_POS: ETHERSCAN_EXPLORER_TX_URL.format(base_url='polygonscan.com'),  # noqa: E501
            SupportedBlockchain.ARBITRUM_ONE: ETHERSCAN_EXPLORER_TX_URL.format(base_url='arbiscan.io'),  # noqa: E501
            SupportedBlockchain.BASE: ETHERSCAN_EXPLORER_TX_URL.format(base_url='basescan.org'),
            SupportedBlockchain.GNOSIS: ETHERSCAN_EXPLORER_TX_URL.format(base_url='gnosisscan.io'),
            SupportedBlockchain.SCROLL: ETHERSCAN_EXPLORER_TX_URL.format(base_url='scrollscan.com'),  # noqa: E501
            SupportedBlockchain.BINANCE_SC: ETHERSCAN_EXPLORER_TX_URL.format(base_url='bscscan.com'),  # noqa: E501
            SupportedBlockchain.ZKSYNC_LITE: 'https://zkscan.io/explorer/transactions/',
        }
        with self.database.conn.read_ctx() as cursor:
            self.reload_settings(cursor)

        frontend_settings = None
        if self.settings.frontend_settings != '':
            try:
                frontend_settings = json.loads(self.settings.frontend_settings)
            except json.decoder.JSONDecodeError as e:
                log.error(
                    'Could not read frontend settings to obtain the blockchain explorers '
                    f'preferences: {e!s}',
                )

        if frontend_settings is not None:
            for chain in EVM_CHAINS_WITH_TRANSACTIONS:
                try:
                    if (
                        'explorers' in frontend_settings and
                        chain.serialize() in frontend_settings['explorers'] and
                        'transaction' in frontend_settings['explorers'][chain.serialize()]
                    ):
                        self.transaction_explorers[chain] = frontend_settings['explorers'][chain.serialize()]['transaction']  # noqa: E501
                except KeyError as e:
                    log.error(f'Could not read explorer for chain {chain} from user settings due to missing key {e!s}')  # noqa: E501

    def _add_sumif_formula(
            self,
            check_range: str,
            condition: str,
            sum_range: str,
            actual_value: FVal,
    ) -> str:
        if self.settings.pnl_csv_with_formulas is False:
            return str(actual_value)

        return f'=SUMIF({check_range};{condition};{sum_range})'

    def _add_pnl_type(
            self,
            event: 'ProcessedAccountingEvent',
            dict_event: dict[str, Any],
            amount_column: str,
            name: Literal['free', 'taxable'],
    ) -> None:
        """Adds the pnl type value and cost basis to the passed dict event"""
        if getattr(event.pnl, name, ZERO) == ZERO:
            return

        index = event.index + CSV_INDEX_OFFSET
        value_formula = f'{amount_column}{index}*H{index}'
        total_value_formula = f'(F{index}*H{index}+G{index}*H{index})'  # formula of both free and taxable  # noqa: E501
        cost_basis_column = 'K' if name == 'taxable' else 'L'
        cost_basis = f'{cost_basis_column}{index}'

        should_count_entire_spend_formula = (
            (name == 'taxable' and event.timestamp >= self.start_ts) or
            (name == 'free' and event.timestamp < self.start_ts)
        )
        if event.count_entire_amount_spend and should_count_entire_spend_formula:
            equation = (
                f'=IF({cost_basis}="",'
                f'-{total_value_formula},'
                f'-{total_value_formula}+{value_formula}-{cost_basis})'
            )
        else:
            equation = (
                f'=IF({cost_basis}="",'
                f'{value_formula},'
                f'{value_formula}-{cost_basis})'
            )

        dict_event[f'pnl_{name}'] = equation
        cost_basis = ''
        if event.cost_basis is not None:
            if self.settings.cost_basis_method == CostBasisMethod.ACB:
                # ACB doesn't have matched acquisitions so we use pure numbers.
                cost_basis = event.cost_basis.taxable_bought_cost if name == 'taxable' else event.cost_basis.taxfree_bought_cost  # type: ignore[assignment]  # noqa: E501
                cost_basis = str(cost_basis) if cost_basis != 0 else ''
            else:  # FIFO, LIFO, HIFO (methods that do have matched acquisitions)
                cost_basis = ''
                for acquisition in event.cost_basis.matched_acquisitions:
                    if name == 'taxable' and acquisition.taxable is False:
                        continue
                    if name == 'free' and acquisition.taxable is True:
                        continue

                    index = acquisition.event.index + CSV_INDEX_OFFSET
                    if cost_basis == '':
                        cost_basis = '='
                    else:
                        cost_basis += '+'

                    cost_basis += f'{acquisition.amount!s}*H{index}'

        dict_event[f'cost_basis_{name}'] = cost_basis

    def _maybe_add_summary(self, events: list[dict[str, Any]], pnls: PnlTotals) -> None:
        """Depending on given settings, adds a few summary lines at the end of
        the all events PnL report"""
        if self.settings.pnl_csv_have_summary is False:
            return

        length = len(events) + 1
        template: dict[str, Any] = {
            'type': '',
            'notes': '',
            'location': '',
            'timestamp': '',
            'asset': '',
            'asset_identifier': '',
            'free_amount': '',
            'taxable_amount': '',
            'price': '',
            'pnl_taxable': '',
            'cost_basis_taxable': '',
            'pnl_free': '',
            'cost_basis_free': '',
        }
        events.extend((template, template))  # separate with 2 new lines

        entry = template.copy()
        entry['taxable_amount'] = 'TAXABLE'
        entry['price'] = 'FREE'
        events.append(entry)

        start_sums_index = length + 4
        sums = 0
        for name, value in pnls.items():
            if value.taxable == ZERO and value.free == ZERO:
                continue
            sums += 1
            entry = template.copy()
            entry['free_amount'] = f'{name!s} total'
            entry['taxable_amount'] = self._add_sumif_formula(
                check_range=f'A2:A{length}',
                condition=f'"{name!s}"',
                sum_range=f'I2:I{length}',
                actual_value=value.taxable,
            )
            entry['price'] = self._add_sumif_formula(
                check_range=f'A2:A{length}',
                condition=f'"{name!s}"',
                sum_range=f'J2:J{length}',
                actual_value=value.free,
            )
            events.append(entry)

        entry = template.copy()
        entry['free_amount'] = 'TOTAL'
        if sums != 0:
            entry['taxable_amount'] = f'=SUM(G{start_sums_index}:G{start_sums_index + sums - 1})'
            entry['price'] = f'=SUM(H{start_sums_index}:H{start_sums_index + sums - 1})'
        else:
            entry['taxable_amount'] = entry['price'] = 0
        events.extend((entry, template, template))  # separate with 2 new lines

        version_result = get_current_version()
        entry = template.copy()
        entry['free_amount'] = 'rotki version'
        entry['taxable_amount'] = version_result.our_version
        events.append(entry)

        for setting in ACCOUNTING_SETTINGS:
            entry = template.copy()
            entry['free_amount'] = setting
            entry['taxable_amount'] = str(getattr(self.settings, setting))
            events.append(entry)

    def create_zip(
            self,
            events: list['ProcessedAccountingEvent'],
            pnls: PnlTotals,
    ) -> tuple[bool, str]:
        dirpath = Path(mkdtemp())
        success, msg = self.export(events=events, pnls=pnls, directory=dirpath)
        if not success:
            return False, msg

        files: list[tuple[Path, str]] = [
            (dirpath / FILENAME_ALL_CSV, FILENAME_ALL_CSV),
        ]
        with ZipFile(file=dirpath / 'csv.zip', mode='w', compression=ZIP_DEFLATED) as csv_zip:
            for path, filename in files:
                if not path.exists():
                    continue

                csv_zip.write(path, filename)
                path.unlink()

        success = False
        filename = ''
        if csv_zip.filename is not None:
            success = True
            filename = csv_zip.filename

        return success, filename

    def to_csv_entry(self, event: 'ProcessedAccountingEvent') -> dict[str, Any]:
        """Prepare the provided event to have a common format for the accounting
        CSV exported file.
        """
        evm_explorer = None
        if event.location in EVM_EVMLIKE_LOCATIONS:
            # provide the explorer url to be used in the notes
            evm_explorer = self.transaction_explorers[SupportedBlockchain.from_location(event.location)]  # type: ignore # type checked via if above # noqa: E501

        dict_event = event.to_exported_dict(
            ts_converter=self.timestamp_to_date,
            export_type=AccountingEventExportType.CSV,
            database=self.database,
            evm_explorer=evm_explorer,
        )
        # For CSV also convert timestamp to date
        dict_event['timestamp'] = self.timestamp_to_date(event.timestamp)
        if self.settings.pnl_csv_with_formulas is False:
            return dict_event

        # else add formulas
        self._add_pnl_type(event=event, dict_event=dict_event, amount_column='F', name='free')
        self._add_pnl_type(event=event, dict_event=dict_event, amount_column='G', name='taxable')
        return dict_event

    def export(
            self,
            events: list['ProcessedAccountingEvent'],
            pnls: PnlTotals,
            directory: Path,
    ) -> tuple[bool, str]:
        serialized_events = [self.to_csv_entry(x) for idx, x in enumerate(events)]
        self._maybe_add_summary(events=serialized_events, pnls=pnls)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            dict_to_csv_file(
                path=directory / FILENAME_ALL_CSV,
                dictionary_list=serialized_events,
                csv_delimiter=self.settings.csv_export_delimiter,
            )
        except (CSVWriteError, PermissionError) as e:
            return False, str(e)

        return True, ''
