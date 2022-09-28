import csv
import logging
from decimal import DivisionByZero
from pathlib import Path
from typing import Any, Dict

from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.data_import.utils import BaseExchangeImporter
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_timestamp
from rotkehlchen.types import Fee, Location, Price, TimestampMS, TradeType
from rotkehlchen.utils.misc import ts_ms_to_sec

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkiGenericTradesImporter(BaseExchangeImporter):
    def _consume_rotki_trades(
            self,
            cursor: DBCursor,
            csv_row: Dict[str, Any],
    ) -> None:
        """Consume rotki generic trades import CSV file.
        May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        - DivisionByZero if `amount_bought` is ZERO
        """
        fee = Fee(deserialize_asset_amount(csv_row['Fee'])) if csv_row['Fee'] else None  # noqa: E501
        fee_currency = (
            symbol_to_asset_or_token(csv_row['Fee Currency'])
            if csv_row['Fee Currency'] and fee is not None else None
        )
        amount_sold = deserialize_asset_amount(csv_row['Sell Amount'])
        amount_bought = deserialize_asset_amount(csv_row['Buy Amount'])
        location = Location.deserialize(csv_row['Location'])
        trade = Trade(
            timestamp=ts_ms_to_sec(
                TimestampMS(deserialize_timestamp(timestamp=csv_row['Timestamp'])),
            ),
            location=location,
            fee=fee,
            fee_currency=fee_currency,
            rate=Price(amount_sold / amount_bought),
            base_asset=symbol_to_asset_or_token(csv_row['Base Currency']),
            quote_asset=symbol_to_asset_or_token(csv_row['Quote Currency']),
            trade_type=TradeType.SELL if csv_row['Type'] == 'Sell' else TradeType.BUY,
            amount=amount_bought,
            notes=csv_row['Description'],
        )
        self.add_trade(cursor, trade)

    def _import_csv(self, cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, 'r', encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    self._consume_rotki_trades(cursor, row)
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During rotki generic trades CSV import, found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during rotki generic trades CSV import. '
                        f'{str(e)}. Ignoring entry',
                    )
                    continue
                except DivisionByZero:
                    self.db.msg_aggregator.add_warning(
                        f'During rotki generic trades import, csv row {str(row)} has zero '
                        f'amount bought. Ignoring entry',
                    )
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {str(e)} in csv row {str(row)}') from e
