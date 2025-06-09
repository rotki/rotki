import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.converters import asset_from_kucoin
from rotkehlchen.data_import.utils import BaseExchangeImporter, hash_csv_row
from rotkehlchen.db.drivers.sqlite import DBCursor
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.utils import get_key_if_has_val
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.swap import (
    create_swap_events,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Location
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class KucoinImporter(BaseExchangeImporter):
    """Kucoin CSV importer"""

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db, name='Kucoin')

    def _import_csv(
            self,
            write_cursor: DBCursor,
            filepath: Path,
            **kwargs: Any,
    ) -> None:
        """
        Import trades from Kucoin. Find out which file
        we are parsing depending on its format.

        May raise:
        - UnsupportedCSVEntry if operation not supported
        - InputError if a column we need is missing
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            start_pos = csvfile.tell()
            first_line = csvfile.readline()
            if 'tradeCreatedAt,symbol,side,price,size,funds,fee,feeCurrency' in first_line:
                date_key = 'tradeCreatedAt'
                tokens_key, splitter = 'symbol', '-'
                trade_type_key = 'side'
                amount_key = 'size'
                rate_key = 'price'
                fee_key = 'fee'
                fee_currency_key = 'feeCurrency'
            elif 'Time,Pair,Side,FilledPrice,FilledPriceCoin,Amount,AmountCoin,Volume,VolumeCoin,Fee,FeeCoin' in first_line:  # noqa: E501
                date_key = 'Time'
                tokens_key, splitter = 'Pair', '/'
                trade_type_key = 'Side'
                amount_key = 'Amount'
                rate_key = 'FilledPrice'
                fee_key = 'Fee'
                fee_currency_key = 'FeeCoin'
            else:
                raise InputError('The given kucoin CSV file format can not be recognized')

            csvfile.seek(start_pos)  # go back to start of the file
            for index, row in enumerate(csv.DictReader(csvfile), start=1):
                try:
                    self.total_entries += 1
                    base, quote = row[tokens_key].split(splitter)
                    fee_currency = get_key_if_has_val(row, fee_currency_key)
                    spend, receive = get_swap_spend_receive(
                        is_buy=deserialize_trade_type_is_buy(row[trade_type_key]),
                        base_asset=asset_from_kucoin(base),
                        quote_asset=asset_from_kucoin(quote),
                        amount=deserialize_fval(row[amount_key]),
                        rate=deserialize_price(row[rate_key]),
                    )
                    self.add_history_events(
                        write_cursor=write_cursor,
                        history_events=create_swap_events(
                            timestamp=ts_sec_to_ms(deserialize_timestamp_from_date(
                                date=row[date_key],
                                formatstr=kwargs.get('timestamp_format', '%Y-%m-%d %H:%M:%S'),
                                location='Kucoin order history import',
                            )),
                            location=Location.KUCOIN,
                            spend=spend,
                            receive=receive,
                            fee=AssetAmount(
                                asset=asset_from_kucoin(fee_currency),
                                amount=deserialize_fval_or_zero(get_key_if_has_val(row, fee_key)),
                            ) if fee_currency is not None else None,
                            event_identifier=f'KU{hash_csv_row(row)}',
                        ),
                    )
                    self.imported_entries += 1
                except DeserializationError as e:
                    self.send_message(
                        row_index=index,
                        csv_row=row,
                        msg=f'Deserialization error: {e!s}.',
                        is_error=True,
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in kucoin csv row {row!s}') from e
