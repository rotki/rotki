"""
Import transactions from the Uphold Platform.
"""
from __future__ import annotations  # isort:skip

import csv
import logging
from pathlib import Path
from typing import Any, Dict

from rotkehlchen.assets.converters import asset_from_uphold
from rotkehlchen.data_import.importers._import_helpers import (
    TransactionType,
    check_transaction_type,
    classify_transaction,
    get_action_type,
)
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetMovementCategory, Fee, Location, TradeType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UpholdTransactionsImporter(BaseExchangeImporter):
    """This class imports transactions from the Uphold Platform."""

    def _consume_uphold_transaction(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
            timestamp_format: str = '%a %b %d %Y %H:%M:%S %Z%z',
    ) -> None:
        """
        Consume the file containing both trades and transactions from uphold.
        This method can raise:
        - UnknownAsset
        - DeserializationError
        - KeyError
        """
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='uphold',
        )
        destination_asset = asset_from_uphold(csv_row['Destination Currency'])
        destination_amount = deserialize_asset_amount(csv_row['Destination Amount'])
        origin_asset = asset_from_uphold(csv_row['Origin Currency'])
        origin_amount = deserialize_asset_amount(csv_row['Origin Amount'])
        fee = deserialize_fee(csv_row['Fee Amount'])
        fee_asset = asset_from_uphold(
            csv_row['Fee Currency'] or csv_row['Origin Currency'],
        )
        transaction_type = csv_row['Type']
        notes = f"""
Activity from uphold with uphold transaction id:
 {csv_row['Id']}, origin: {csv_row['Origin']},
 and destination: {csv_row['Destination']}.
  Type: {csv_row['Type']}.
  Status: {csv_row['Status']}.
"""

        # Checks for valid transactions
        if 'uphold' not in csv_row:
            log.error(f'This transaction seems to be unrelated to uphold: {csv_row}')
            raise KeyError('"uphold" does not appear in the csv row.')

        check_transaction_type(
            transaction_type=transaction_type,
            origin=csv_row['Origin'],
            destination=csv_row['Destination'],
            target_platform=__name__.split('_', maxsplit=1)[0],
        )

        transaction_handler = classify_transaction(
            origin=csv_row['Origin'],
            destination=csv_row['Destination'],
            origin_asset=origin_asset,
            destination_asset=destination_asset,
            origin_amount=origin_amount,
            destination_amount=destination_amount,
            transaction_type=transaction_type,
        )
        if transaction_handler == TransactionType.AssetMovement:
            self.add_asset_movement(
                cursor,
                asset_movement=transaction_handler(
                    location=Location.UPHOLD,
                    category=AssetMovementCategory.WITHDRAWAL,
                    timestamp=timestamp,
                    asset=origin_asset,
                    amount=origin_amount,
                    fee=Fee(fee),
                    fee_asset=fee_asset,
                ),
            )
        elif transaction_handler == TransactionType.Trade:
            self.add_trade(
                cursor=cursor,
                trade=transaction_handler(
                    timestamp=timestamp,
                    location=Location.UPHOLD,
                    quote_asset=destination_asset,
                    base_asset=origin_asset,
                    destination_amount=destination_amount,
                    origin_amount=origin_amount,
                    trade_type=TradeType.BUY,
                    fee=Fee(fee),
                    fee_asset=fee_asset,
                    notes=notes,
                ),
            )
        elif transaction_handler == TransactionType.LedgerAction:
            self.add_ledger_action(
                cursor=cursor,
                ledger_action=transaction_handler(
                    action_type=get_action_type(transaction_type),
                    timestamp=timestamp,
                    destination_amount=destination_amount,
                    destination_asset=destination_asset,
                    notes=notes,
                    location=Location.UPHOLD,
                ),
            )

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Information for the values that the columns can have has been obtained from sample CSVs
        """
        with open(filepath, "r", encoding="utf-8-sig") as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_uphold_transaction(cursor, row, **kwargs)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f"During uphold CSV import found action with unknown "
                        f"asset {e.asset_name}. Ignoring entry",
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f"Deserialization error during uphold CSV import. "
                        f"{str(e)}. Ignoring entry",
                    )
                    continue
                except KeyError as e:
                    raise InputError(
                        f"Could not find key {str(e)} in csv row {str(row)}",
                    ) from e
