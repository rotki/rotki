import json
import logging
from csv import DictWriter
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any, Dict, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from rotkehlchen.accounting.pnl import PnlTotals
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.accounting.processed_event import ProcessedAccountingEvent
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

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
        w = DictWriter(f, fieldnames=dictionary_list[0].keys())
        w.writeheader()
        try:
            for dic in dictionary_list:
                w.writerow(dic)
        except ValueError as e:
            raise CSVWriteError(f'Failed to write {path} CSV due to {str(e)}') from e


class CSVExporter(CustomizableDateMixin):

    def __init__(
            self,
            database: 'DBHandler',
    ):
        super().__init__(database=database)
        self.reset()

    def reset(self) -> None:
        self.reload_settings()
        try:
            frontend_settings = json.loads(self.settings.frontend_settings)
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

    def _add_if_formula(
            self,
            condition: str,
            if_true: str,
            if_false: str,
            actual_value: FVal,
    ) -> str:
        if self.settings.pnl_csv_with_formulas is False:
            return str(actual_value)

        return f'=IF({condition};{if_true};{if_false})'

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

    def _add_equals_formula(self, expression: str, actual_value: FVal) -> str:
        if self.settings.pnl_csv_with_formulas is False:
            return str(actual_value)

        return f'={expression}'

    def _maybe_add_summary(self, events: List[Dict[str, Any]], pnls: PnlTotals) -> None:
        """Depending on given settings, adds a few summary lines at the end of
        the all events PnL report"""
        if self.settings.pnl_csv_have_summary is False:
            return

        length = len(events) + 1
        template: Dict[str, Any] = {
            'type': '',
            'notes': '',
            'location': '',
            'timestamp': '',
            'asset': '',
            'free_amount': '',
            'taxable_amount': '',
            'price': '',
            'pnl': '',
            'cost_basis': '',
        }
        events.append(template)  # separate with 2 new lines
        events.append(template)

        total_value = pnls.get_net_taxable_pnl()
        for name, value in pnls.items():
            entry = template.copy()
            entry['free_amount'] = name.upper()
            entry['taxable_amount'] = self._add_sumif_formula(
                check_range=f'A2:A{length}',
                condition=f'"{name.upper()}"',
                sum_range=f'I2:I{length}',
                actual_value=value,
            )
            events.append(entry)

        entry = template.copy()
        entry['free_amount'] = 'TOTAL'
        entry['taxable_amount'] = total_value

        version_result = get_current_version(check_for_updates=False)
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
            events: List['ProcessedAccountingEvent'],
            pnls: PnlTotals,
    ) -> Tuple[bool, str]:
        # TODO: Find a way to properly delete the directory after send is complete
        dirpath = Path(mkdtemp())
        success, msg = self.export(events=events, pnls=pnls, directory=dirpath)
        if not success:
            return False, msg

        files: List[Tuple[Path, str]] = [
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

    def export(
            self,
            events: List['ProcessedAccountingEvent'],
            pnls: PnlTotals,
            directory: Path,
    ) -> Tuple[bool, str]:
        serialized_events = [x.to_exported_dict(self.timestamp_to_date) for x in events]
        self._maybe_add_summary(events=serialized_events, pnls=pnls)
        try:
            directory.mkdir(parents=True, exist_ok=True)
            _dict_to_csv_file(
                directory / FILENAME_ALL_CSV,
                serialized_events,
            )
        except (CSVWriteError, PermissionError) as e:
            return False, str(e)

        return True, ''
