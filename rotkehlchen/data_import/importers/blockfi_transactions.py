import csv
import logging
from pathlib import Path
from typing import Any, Dict

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.converters import asset_from_blockfi
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, AssetMovementCategory, Fee, Location

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BlockfiTransactionsImporter(BaseExchangeImporter):
    def _consume_blockfi_entry(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
            timestamp_format: str = '%Y-%m-%d %H:%M:%S',
    ) -> None:
        """
        Process entry for BlockFi transaction history. Trades for this file are ignored
        and instead should be extracted from the file containing only trades.
        This method can raise:
        - UnsupportedBlockFiEntry
        - UnknownAsset
        - DeserializationError
        """
        if len(csv_row['Confirmed At']) != 0:
            timestamp = deserialize_timestamp_from_date(
                date=csv_row['Confirmed At'],
                formatstr=timestamp_format,
                location='BlockFi',
            )
        else:
            log.debug(f'Ignoring unconfirmed BlockFi entry {csv_row}')
            return

        asset = asset_from_blockfi(csv_row['Cryptocurrency'])
        raw_amount = deserialize_asset_amount(csv_row['Amount'])
        abs_amount = AssetAmount(abs(raw_amount))
        entry_type = csv_row['Transaction Type']
        # BlockFI doesn't provide information about fees
        fee = Fee(ZERO)
        fee_asset = A_USD  # Can be whatever

        if entry_type in ('Deposit', 'Wire Deposit', 'ACH Deposit'):
            asset_movement = AssetMovement(
                location=Location.BLOCKFI,
                category=AssetMovementCategory.DEPOSIT,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=abs_amount,
                fee=fee,
                fee_asset=fee_asset,
                link='',
            )
            self.add_asset_movement(cursor, asset_movement)
        elif entry_type in ('Withdrawal', 'Wire Withdrawal', 'ACH Withdrawal'):
            asset_movement = AssetMovement(
                location=Location.BLOCKFI,
                category=AssetMovementCategory.WITHDRAWAL,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=abs_amount,
                fee=fee,
                fee_asset=fee_asset,
                link='',
            )
            self.add_asset_movement(cursor, asset_movement)
        elif entry_type == 'Withdrawal Fee':
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.EXPENSE,
                location=Location.BLOCKFI,
                amount=abs_amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=f'{entry_type} from BlockFi',
            )
            self.add_ledger_action(cursor, action)
        elif entry_type in ('Interest Payment', 'Bonus Payment', 'Referral Bonus'):
            action = LedgerAction(
                identifier=0,  # whatever is not used at insertion
                timestamp=timestamp,
                action_type=LedgerActionType.INCOME,
                location=Location.BLOCKFI,
                amount=abs_amount,
                asset=asset,
                rate=None,
                rate_asset=None,
                link=None,
                notes=f'{entry_type} from BlockFi',
            )
            self.add_ledger_action(cursor, action)
        elif entry_type == 'Crypto Transfer':
            category = (
                AssetMovementCategory.WITHDRAWAL if raw_amount < ZERO
                else AssetMovementCategory.DEPOSIT
            )
            asset_movement = AssetMovement(
                location=Location.BLOCKFI,
                category=category,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=abs_amount,
                fee=fee,
                fee_asset=fee_asset,
                link='',
            )
            self.add_asset_movement(cursor, asset_movement)
        elif entry_type == 'Trade':
            pass
        else:
            raise UnsupportedCSVEntry(f'Unsuported entry {entry_type}. Data: {csv_row}')

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from
        https://github.com/BittyTax/BittyTax/blob/06794f51223398759852d6853bc7112ffb96129a/bittytax/conv/parsers/blockfi.py#L67
        May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_blockfi_entry(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During BlockFi CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during BlockFi CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
