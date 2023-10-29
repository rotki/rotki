import csv
import logging
from pathlib import Path
from typing import Any

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, AssetMovementCategory, Fee, Location
from rotkehlchen.utils.misc import satoshis_to_btc

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitMEXImporter(BaseExchangeImporter):
    @staticmethod
    def _consume_realised_pnl(
            csv_row: dict[str, Any], timestamp_format: str = '%m/%d/%Y, %H:%M:%S %p',
    ) -> MarginPosition:
        """
        Use entries resulting from Realised PnL to generate a MarginPosition object.
        May raise:
        - KeyError
        - DeserializationError
        """
        close_time = deserialize_timestamp_from_date(
            date=csv_row['transactTime'],
            formatstr=timestamp_format,
            location='Bitmex Wallet History Import',
        )
        realised_pnl = AssetAmount(satoshis_to_btc(deserialize_asset_amount(csv_row['amount'])))
        fee = deserialize_fee(csv_row['fee']) if csv_row['fee'] != 'null' else Fee(ZERO)
        notes = f"PnL from trade on {csv_row['address']}"
        log.debug(
            'Processing Bitmex Realised PnL',
            timestamp=close_time,
            profit_loss=realised_pnl,
            fee=fee,
            notes=notes,
        )
        usd_price = PriceHistorian().query_historical_price(A_BTC, A_USD, close_time)
        abs_amount = abs(realised_pnl)
        asset_balance = AssetBalance(A_BTC, Balance(abs_amount, usd_price * abs_amount))
        return MarginPosition(
            location=Location.BITMEX,
            open_time=None,
            close_time=close_time,
            profit_loss=realised_pnl,
            pl_currency=asset_balance.asset,
            fee=fee,
            fee_currency=asset_balance.asset,
            notes=notes,
            link=f'Imported from BitMEX CSV file. Transact Type: {csv_row["transactType"]}',
        )

    @staticmethod
    def _consume_deposits_or_withdrawals(
            csv_row: dict[str, Any], timestamp_format: str = '%m/%d/%Y, %H:%M:%S %p',
    ) -> AssetMovement:
        """
        Use Deposit and Withdrawal entries to generate an AssetMovement object.
        May raise:
        - KeyError
        - DeserializationError
        """
        asset = A_BTC.resolve_to_asset_with_oracles()
        amount = deserialize_asset_amount_force_positive(csv_row['amount'])
        fee = deserialize_fee(csv_row['fee']) if csv_row['fee'] != 'null' else Fee(ZERO)
        transact_type = csv_row['transactType']
        category = AssetMovementCategory.DEPOSIT if transact_type == 'Deposit' else AssetMovementCategory.WITHDRAWAL  # noqa: E501
        amount = AssetAmount(satoshis_to_btc(amount))  # bitmex stores amounts in satoshis
        fee = Fee(satoshis_to_btc(fee))
        ts = deserialize_timestamp_from_date(
            date=csv_row['transactTime'],
            formatstr=timestamp_format,
            location='Bitmex Wallet History Import',
        )
        return AssetMovement(
            location=Location.BITMEX,
            category=category,
            address=deserialize_asset_movement_address(csv_row, 'address', asset),
            transaction_id=get_key_if_has_val(csv_row, 'tx'),
            timestamp=ts,
            asset=asset,
            amount=amount,
            fee_asset=asset,
            fee=fee,
            link=f'Imported from BitMEX CSV file. Transact Type: {transact_type}',
        )

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """
        Import deposits, withdrawals and realised pnl events from BitMEX.
        May raise:
        - UnsupportedCSVEntry if operation not supported
        - InputError if a column we need is missing
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.DictReader(csvfile)
            for row in data:
                try:
                    if row['transactType'] == 'RealisedPNL':
                        margin_position = self._consume_realised_pnl(row, **kwargs)
                        self.add_margin_trade(write_cursor, margin_position)
                    elif row['transactType'] in {'Deposit', 'Withdrawal'}:
                        if row['transactStatus'] == 'Completed':
                            self.add_asset_movement(
                                write_cursor, self._consume_deposits_or_withdrawals(row, **kwargs),
                            )
                    else:
                        raise UnsupportedCSVEntry(
                            f'transactType {row["transactType"]} is not currently supported',
                        )
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Deserialization error during BitMEX CSV import. '
                        f'{e!s}. Ignoring entry',
                    )
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
