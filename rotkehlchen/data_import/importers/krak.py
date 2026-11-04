import csv
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.importers.constants import KRAK_EVENT_PREFIX
from rotkehlchen.data_import.utils import (
    BaseExchangeImporter,
    SkippedCSVEntry,
    UnsupportedCSVEntry,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events_multi_fee
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_KRAK
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, Timezone
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import TimestampMS


KRAK_DATE_FORMAT: Final = '%Y-%m-%d %H:%M:%S'
KRAK_MAX_DECIMALS: Final = 10  # the most decimals Krak writes for an amount
KRAK_PLACEHOLDER: Final = '-'  # Value Krak exports for fields of rows that have not settled yet
REQUIRED_COLUMNS: Final = (
    'Date (UTC)', 'Type', 'Subtype', 'Asset', 'Wallet', 'Amount', 'Counter party', 'Reference',
)
TRADE_TYPE: Final = 'Trade'
CARD_TYPE: Final = 'Krak Card'
CARD_PAYMENT_SUBTYPE: Final = 'Card Payment'
CASHBACK_SUBTYPE: Final = 'Cashback Reward'
CASHBACK_WINDOW_MS: Final = 60000  # Krak pays the cashback seconds after the card payment
CASHBACK_SEQUENCE_INDEX: Final = 2  # after the card payment and its fee
PENDING_COLUMN_PREFIXES: Final = ('Price', 'Fee', 'Value')  # columns Krak fills on settlement


class KrakRow:
    """A parsed row of a Krak activity export.

    Amounts are signed: negative means the asset left the account. The balance change of a row
    is `amount - fee`, with the fee denominated in the row's asset.
    """

    def __init__(
            self,
            index: int,
            raw: dict[str, Any],
            fiat_fee_column: str | None,
            price_column: str | None,
    ) -> None:
        """May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        self.index = index
        self.raw = raw
        self.is_pending = any(
            value == KRAK_PLACEHOLDER for column, value in raw.items()
            if column.startswith(PENDING_COLUMN_PREFIXES)
        )
        self.type: str = raw['Type']
        self.subtype: str = raw['Subtype']
        self.reference: str = raw['Reference']
        self.counterparty: str = raw['Counter party'].strip()
        self.wallet: str | None = raw['Wallet'] or None
        self.timestamp: TimestampMS = ts_sec_to_ms(deserialize_timestamp_from_date(
            date=raw['Date (UTC)'],
            formatstr=KRAK_DATE_FORMAT,
            location='Krak',
            timezone_name=Timezone('UTC'),
        ))
        self.asset: AssetWithOracles = asset_from_kraken(raw['Asset'])
        self.amount = _deserialize_krak_number(raw['Amount'])
        self.fee = ZERO if self.is_pending else self._deserialize_fee(fiat_fee_column=fiat_fee_column, price_column=price_column)  # noqa: E501

    def _deserialize_fee(self, fiat_fee_column: str | None, price_column: str | None) -> FVal:
        """Read the fee in the row's asset. Exports before November 2026 only carry the fee in
        fiat, in which case it is converted back with the row's price.

        May raise DeserializationError.
        """
        if (fee := self.raw.get('Fee')) is not None:
            return abs(_deserialize_krak_number(fee))

        if (
            fiat_fee_column is None or
            price_column is None or
            (fiat_fee := _deserialize_krak_number(self.raw[fiat_fee_column])) == ZERO or
            (price := _deserialize_krak_number(self.raw[price_column])) == ZERO
        ):
            return ZERO

        return round(abs(fiat_fee / price), KRAK_MAX_DECIMALS)

    def ensure_settled(self) -> None:
        """May raise SkippedCSVEntry if the row is still pending"""
        if self.is_pending:
            raise SkippedCSVEntry(
                f'Skipped pending {self.type} activity {self.reference}. '
                'Import a later Krak export once it has settled',
            )

    def group_identifier(self) -> str:
        return f'{KRAK_EVENT_PREFIX}_{self.reference}'

    def counterparty_hint(self) -> str:
        return f' {self.counterparty}' if self.counterparty != '' else ''


def _deserialize_krak_number(value: str) -> FVal:
    """Krak writes thousands separators inside quoted numbers. May raise DeserializationError"""
    return deserialize_fval(value.replace(',', ''), name='krak number', location='Krak')


def _find_fiat_column(header: Sequence[str], prefix: str) -> str | None:
    """Find the fiat denominated column, e.g. `Fee (EUR)`. Its currency is the account's."""
    return next((column for column in header if column.startswith(prefix)), None)


def _match_cashbacks_to_payments(rows: Sequence[KrakRow]) -> dict[int, KrakRow]:
    """Find the card payment of each cashback row. The result is keyed by the cashback row index.

    Krak gives the two rows unrelated references, so they are matched by wallet and counterparty,
    with the cashback following the payment within CASHBACK_WINDOW_MS. A burst of payments to one
    merchant is matched oldest first.

    Pending rows take part so that a cashback ends up in the same group whether or not its payment
    has settled, since that group is what deduplicates a later import.
    """
    open_payments: defaultdict[tuple[str | None, str], deque[KrakRow]] = defaultdict(deque)
    payments: dict[int, KrakRow] = {}
    for row in sorted(rows, key=lambda x: x.timestamp):  # stable, so ties keep the file order
        if row.type != CARD_TYPE:
            continue

        merchant_payments = open_payments[row.wallet, row.counterparty]
        if row.subtype == CARD_PAYMENT_SUBTYPE and row.amount < ZERO:
            merchant_payments.append(row)
        elif row.subtype == CASHBACK_SUBTYPE and row.amount > ZERO:
            while (
                len(merchant_payments) != 0 and
                row.timestamp - merchant_payments[0].timestamp > CASHBACK_WINDOW_MS
            ):
                merchant_payments.popleft()

            if len(merchant_payments) != 0:
                payments[row.index] = merchant_payments.popleft()

    return payments


class KrakImporter(BaseExchangeImporter):
    """Importer for the activity CSV exported from the Krak app"""

    def __init__(self, db: DBHandler) -> None:
        super().__init__(db=db, name='Krak')

    def _fee_event(
            self,
            row: KrakRow,
            event_type: HistoryEventType,
            group_row: KrakRow | None = None,
            sequence_index: int = 1,
    ) -> list[HistoryBaseEntry]:
        if row.fee == ZERO:
            return []

        group_row = group_row or row
        return [HistoryEvent(
            group_identifier=group_row.group_identifier(),
            sequence_index=sequence_index,
            timestamp=group_row.timestamp,
            location=LOCATION_KRAK,
            event_type=event_type,
            event_subtype=HistoryEventSubType.FEE,
            asset=row.asset,
            amount=row.fee,
            location_label=row.wallet,
            notes=f'Pay {row.fee} {row.asset.symbol_or_name()} as Krak fee',
        )]

    def _asset_movement(
            self,
            row: KrakRow,
            notes: str | None = None,
            is_transfer: bool = False,
    ) -> list[HistoryBaseEntry]:
        """Create a deposit or withdrawal. Transfers are tagged so that movement matching
        pairs them with the Kraken side, even when they are in fiat."""
        extra_data: AssetMovementExtraData = {'reference': row.reference}
        if is_transfer:
            extra_data['krak_transfer'] = True

        events: list[HistoryBaseEntry] = [AssetMovement(
            group_identifier=row.group_identifier(),
            location=LOCATION_KRAK,
            event_subtype=HistoryEventSubType.SPEND if row.amount < ZERO else HistoryEventSubType.RECEIVE,  # noqa: E501
            timestamp=row.timestamp,
            asset=row.asset,
            amount=abs(row.amount),
            location_label=row.wallet,
            notes=notes,
            extra_data=extra_data,
        )]
        if row.fee != ZERO:
            events.append(AssetMovement(
                group_identifier=row.group_identifier(),
                location=LOCATION_KRAK,
                event_subtype=HistoryEventSubType.FEE,
                timestamp=row.timestamp,
                asset=row.asset,
                amount=row.fee,
                location_label=row.wallet,
            ))
        return events

    def _history_event(
            self,
            row: KrakRow,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            notes: str,
            group_row: KrakRow | None = None,
            sequence_index: int = 0,
    ) -> list[HistoryBaseEntry]:
        """Create the event of a row and its fee. They take the group and timestamp of group_row
        when given, since events of one group are sorted by timestamp before sequence index."""
        anchor = group_row or row
        return [HistoryEvent(
            group_identifier=anchor.group_identifier(),
            sequence_index=sequence_index,
            timestamp=anchor.timestamp,
            location=LOCATION_KRAK,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=row.asset,
            amount=abs(row.amount),
            location_label=row.wallet,
            notes=notes,
        ), *self._fee_event(
            row=row,
            event_type=HistoryEventType.SPEND,
            group_row=group_row,
            sequence_index=sequence_index + 1,
        )]

    def _events_for_row(
            self,
            row: KrakRow,
            cashback_payment: KrakRow | None = None,
    ) -> list[HistoryBaseEntry]:
        """Turn a single, non trade, Krak row into events. A cashback joins the group and takes
        the timestamp of its card payment, given as cashback_payment, so it follows the payment.

        May raise:
        - UnsupportedCSVEntry if the type/subtype/sign combination is not known
        - SkippedCSVEntry if the row is a cashback whose card payment is not in the file
        """
        amount_str = f'{abs(row.amount)} {row.asset.symbol_or_name()}'
        match (row.type, row.subtype):
            case ('Third Party Payment', 'Deposit' | 'Withdrawal'):
                return self._asset_movement(
                    row=row,
                    notes=f'Krak {row.subtype.lower()} {"to" if row.amount < ZERO else "from"}{row.counterparty_hint()}' if row.counterparty != '' else None,  # noqa: E501
                )
            case ('Transfer', ''):
                if row.counterparty == '':  # payments between Krak users, not movements
                    if row.amount < ZERO:
                        return self._history_event(
                            row=row,
                            event_type=HistoryEventType.SPEND,
                            event_subtype=HistoryEventSubType.NONE,
                            notes=f'Send {amount_str} to another Krak user',
                        )
                    return self._history_event(
                        row=row,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.NONE,
                        notes=f'Receive {amount_str} from another Krak user',
                    )
                return self._asset_movement(
                    row=row,
                    is_transfer=True,
                    notes=f'Krak transfer {"to" if row.amount < ZERO else "from"}{row.counterparty_hint()}',  # noqa: E501
                )
            case ('Krak Card', 'Card Payment'):
                if row.amount > ZERO:
                    return self._history_event(
                        row=row,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.REFUND,
                        notes=f'Receive {amount_str} as Krak card refund from{row.counterparty_hint()}',  # noqa: E501
                    )
                return self._history_event(
                    row=row,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.PAYMENT,
                    notes=f'Pay {amount_str} with the Krak card to{row.counterparty_hint()}',
                )
            case ('Krak Card', 'Cashback Reward') if row.amount > ZERO:
                if cashback_payment is None:
                    raise SkippedCSVEntry(
                        f'Skipped Krak cashback {row.reference} since its card payment is not in '
                        'this export. Import an export that contains both',
                    )

                return self._history_event(
                    row=row,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.CASHBACK,
                    notes=f'Receive {amount_str} as Krak card cashback for a payment to{row.counterparty_hint()}',  # noqa: E501
                    group_row=cashback_payment,
                    sequence_index=CASHBACK_SEQUENCE_INDEX,
                )
            case ('Earn', 'Reward') if row.amount > ZERO:
                return [HistoryEvent(
                    group_identifier=row.group_identifier(),
                    sequence_index=0,
                    timestamp=row.timestamp,
                    location=LOCATION_KRAK,
                    event_type=HistoryEventType.STAKING,
                    event_subtype=HistoryEventSubType.REWARD,
                    asset=row.asset,
                    amount=row.amount,
                    location_label=row.wallet,
                    notes=f'Receive {amount_str} as Krak earn reward',
                ), *self._fee_event(row=row, event_type=HistoryEventType.STAKING)]

        raise UnsupportedCSVEntry(
            f'Unsupported Krak entry {row.type}/{row.subtype} with amount {row.amount}',
        )

    def _events_for_trade(self, legs: list[KrakRow]) -> list[HistoryBaseEntry]:
        """Turn the two legs of a Krak trade, which share a reference, into a swap.

        The direction of each leg comes from the sign of its amount. Krak labels the outgoing
        leg of a crypto funded payment as `Buy`, so the subtype can't be trusted for it.

        May raise:
        - UnsupportedCSVEntry if the legs are not one outgoing and one incoming
        """
        if (
            len(legs) != 2 or
            len(spend_legs := [x for x in legs if x.amount < ZERO]) != 1 or
            len(receive_legs := [x for x in legs if x.amount > ZERO]) != 1
        ):
            raise UnsupportedCSVEntry(
                f'Krak trade {legs[0].reference} does not have exactly one '
                f'outgoing and one incoming leg',
            )

        spend, receive = spend_legs[0], receive_legs[0]
        return list(create_swap_events_multi_fee(
            timestamp=spend.timestamp,
            location=LOCATION_KRAK,
            spend=AssetAmount(asset=spend.asset, amount=abs(spend.amount)),
            receive=AssetAmount(asset=receive.asset, amount=receive.amount),
            group_identifier=spend.group_identifier(),
            fees=[
                (AssetAmount(asset=leg.asset, amount=leg.fee), None, None)
                for leg in (spend, receive) if leg.fee != ZERO
            ],
            location_label=spend.wallet,
            spend_notes=(
                f'Krak {spend.subtype.lower()} with{spend.counterparty_hint()}'
                if spend.counterparty not in ('', 'Krak') else None
            ),
        ))

    def _import_csv(self, write_cursor: DBCursor, filepath: Path, **kwargs: Any) -> None:
        """Import a Krak activity export. Timestamps are always UTC so the timestamp format
        and timezone arguments are ignored.

        May raise InputError if the file is not a Krak activity export.
        """
        rows: list[KrakRow] = []
        with open(filepath, encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            header = reader.fieldnames or []
            if len(missing := [x for x in REQUIRED_COLUMNS if x not in header]) != 0:
                raise InputError(f'Krak CSV is missing the columns {", ".join(missing)}')

            fiat_fee_column = _find_fiat_column(header=header, prefix='Fee (')
            price_column = _find_fiat_column(header=header, prefix='Price (')
            for index, raw_row in enumerate(reader, start=1):
                self.total_entries += 1
                try:
                    rows.append(KrakRow(
                        index=index,
                        raw=raw_row,
                        fiat_fee_column=fiat_fee_column,
                        price_column=price_column,
                    ))
                except UnknownAsset as e:
                    self.send_message(
                        row_index=index,
                        csv_row=raw_row,
                        msg=f'Unknown asset {e.identifier}.',
                        is_error=True,
                    )
                except DeserializationError as e:
                    self.send_message(row_index=index, csv_row=raw_row, msg=str(e), is_error=True)
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {raw_row!s}') from e

        trades: defaultdict[str, list[KrakRow]] = defaultdict(list)
        cashback_payments = _match_cashbacks_to_payments(rows)
        for row in rows:
            try:
                row.ensure_settled()
                if row.type == TRADE_TYPE:
                    trades[row.reference].append(row)
                    continue

                self.add_history_events(write_cursor, self._events_for_row(
                    row=row,
                    cashback_payment=cashback_payments.get(row.index),
                ))
                self.imported_entries += 1
            except SkippedCSVEntry as e:
                self.send_message(row_index=row.index, csv_row=row.raw, msg=str(e), is_error=False)
            except UnsupportedCSVEntry as e:
                self.send_message(row_index=row.index, csv_row=row.raw, msg=str(e), is_error=True)

        for legs in trades.values():
            try:
                self.add_history_events(write_cursor, self._events_for_trade(legs))
                self.imported_entries += len(legs)
            except UnsupportedCSVEntry as e:
                for leg in legs:
                    self.send_message(row_index=leg.index, csv_row=leg.raw, msg=str(e), is_error=True)  # noqa: E501
