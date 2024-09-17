import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_nexo
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    SkippedCSVEntry,
    UnsupportedCSVEntry,
    hash_csv_row,
)
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetMovementCategory, Fee, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


NEXO_PREFIX = 'NEXO_'


class NexoImporter(BaseExchangeImporter):
    """Nexo CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Nexo')

    def _consume_nexo(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """
        Consume CSV file from NEXO.
        This method can raise:
        - UnsupportedNexoEntry
        - UnknownAsset
        - DeserializationError
        """
        ignored_entries = (
            'ExchangeToWithdraw',
            'DepositToExchange',
            'Repayment',  # informational loan operation
            'UnlockingTermDeposit',  # Move between nexo wallets
            'LockingTermDeposit',  # Move between nexo wallets
            'TransferIn',  # Transfer between nexo wallets
            'TransferOut',  # Transfer between nexo wallets
        )

        if 'rejected' not in csv_row['Details']:
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Date / Time'],
                formatstr=timestamp_format,
                location='NEXO',
            )
        else:
            raise SkippedCSVEntry('Ignoring rejected entry.')

        asset = asset_from_nexo(csv_row['Output Currency'])
        amount = deserialize_asset_amount_force_positive(csv_row['Output Amount'])
        entry_type = csv_row['Type']
        transaction = csv_row['Transaction']

        if entry_type in {'Exchange', 'CreditCardStatus'}:
            raise UnsupportedCSVEntry(
                'Found exchange/credit card status transaction in nexo csv import but the entry '
                'will be ignored since not enough information is provided about the trade.',
            )
        if entry_type in {'Deposit', 'ExchangeDepositedOn'}:
            asset_movement = AssetMovement(
                location=Location.NEXO,
                category=AssetMovementCategory.DEPOSIT,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=Fee(ZERO),
                fee_asset=A_USD,
                link=transaction,
            )
            self.add_asset_movement(write_cursor, asset_movement)
        elif entry_type in {'Withdrawal', 'WithdrawExchanged'}:
            asset_movement = AssetMovement(
                location=Location.NEXO,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=Fee(ZERO),
                fee_asset=A_USD,
                link=transaction,
            )
            self.add_asset_movement(write_cursor, asset_movement)
        elif entry_type == 'Withdrawal Fee':
            event = HistoryEvent(
                event_identifier=f'{NEXO_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.NEXO,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                balance=Balance(amount=amount),
                asset=asset,
                location_label=transaction,
                notes=f'{entry_type} from Nexo',
            )
            self.add_history_events(write_cursor, [event])
        elif entry_type in {'Interest', 'Bonus', 'Dividend', 'FixedTermInterest', 'Cashback', 'ReferralBonus'}:  # noqa: E501
            # A user shared a CSV file where some entries marked as interest had negative amounts.
            # we couldn't find information about this since they seem internal transactions made
            # by nexo but they appear like a trade from asset -> nexo in order to gain interest
            # in nexo. There seems to always be another entry with the amount that the user
            # received so we'll ignore interest rows with negative amounts.
            if deserialize_asset_amount(csv_row['Output Amount']) < 0:
                log.debug(f'Ignoring nexo entry {csv_row} with negative interest')
                return

            event = HistoryEvent(
                event_identifier=f'{NEXO_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.NEXO,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                balance=Balance(amount=amount),
                asset=asset,
                location_label=transaction,
                notes=f'{entry_type} from Nexo',
            )
            self.add_history_events(write_cursor, [event])
        elif entry_type == 'Liquidation':
            input_asset = asset_from_nexo(csv_row['Input Currency'])
            input_amount = deserialize_asset_amount_force_positive(csv_row['Input Amount'])
            event = HistoryEvent(
                event_identifier=f'{NEXO_PREFIX}{hash_csv_row(csv_row)}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.NEXO,
                event_type=HistoryEventType.LOSS,
                event_subtype=HistoryEventSubType.LIQUIDATE,
                balance=Balance(amount=input_amount),
                asset=input_asset,
                location_label=transaction,
                notes=f'{entry_type} from Nexo',
            )
            self.add_history_events(write_cursor, [event])
        elif entry_type in ignored_entries:
            pass
        else:
            raise UnsupportedCSVEntry(f'Unsuported entry {entry_type}. Data: {csv_row}')

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/nexo.py
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    self._consume_nexo(write_cursor, row, **kwargs)
                    self.imported_entries += 1
                except UnknownAsset as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Unknown asset {e.identifier}.',
                        is_error=True,
                    )
                except DeserializationError as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Deserialization error: {e!s}.',
                        is_error=True,
                    )
                except UnsupportedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=True,
                    )
                except SkippedCSVEntry as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=str(e),
                        is_error=False,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
