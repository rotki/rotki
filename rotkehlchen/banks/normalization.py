"""The canonical shape every bank connector emits, and its mapping onto history events.

Connectors deserialize the bank's payloads into BankAccount / BankTransaction. The
framework turns transactions into HistoryEvent entries so that accounting, the history
view, balances and dedup all work the way they do for every other location.
"""
import hashlib
from dataclasses import dataclass
from enum import auto
from typing import TYPE_CHECKING, Any

from rotkehlchen.constants import ZERO
from rotkehlchen.history.events.structures.bank_transaction import (
    BankTransactionEvent,
    BankTransactionExtraData,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import Location, Timestamp, TimestampMS


class BankTransactionSide(SerializableEnumNameMixin):
    CREDIT = auto()  # money came into the account
    DEBIT = auto()  # money left the account


class BankTransactionKind(SerializableEnumNameMixin):
    TRANSFER = auto()
    CARD = auto()
    DIRECT_DEBIT = auto()
    FEE = auto()  # charged by the bank itself
    INTEREST = auto()
    OTHER = auto()


@dataclass(frozen=True)
class BankAccount:
    identifier: str  # the bank's stable id of the account
    name: str
    asset: AssetWithOracles  # the account currency, as a rotki fiat asset
    balance: FVal  # settled balance
    iban: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class BankTransaction:
    """A settled, final bank transaction. Connectors never emit pending ones."""
    source_id: str  # the bank's stable id, or a content hash from `content_hash_id`
    account_id: str
    timestamp: TimestampMS  # when the money moved (settlement)
    asset: AssetWithOracles
    amount: FVal  # always positive, direction is `side`
    side: BankTransactionSide
    kind: BankTransactionKind
    counterparty_name: str | None = None
    counterparty_account: str | None = None  # IBAN or whatever the bank shows
    reference: str | None = None  # the payment reference / description
    updated_at: Timestamp | None = None  # the bank's last-modified time, feeds the cursor

    def validate(self) -> None:
        if self.amount <= ZERO:
            raise ValueError(f'bank transaction {self.source_id} amount must be positive')
        if self.source_id == '':
            raise ValueError('bank transaction source_id must not be empty')


def content_hash_id(*parts: Any) -> str:
    """Deterministic identity for banks that do not provide a stable transaction id.

    Feed it everything that distinguishes a transaction (account, timestamp, amount, side,
    counterparty, reference); the same real transaction then always hashes the same.
    """
    return hashlib.sha256('|'.join(str(part) for part in parts).encode()).hexdigest()


def bank_transaction_to_events(
        transaction: BankTransaction,
        location: Location,
        location_label: str,
) -> list[BankTransactionEvent]:
    """Map a normalized bank transaction onto rotki history events.

    The group identifier is derived from the location and the source id so that
    re-ingesting the same transaction (a re-sync, a file import overlapping a sync) is a
    no-op at the DB's UNIQUE(group_identifier, sequence_index) constraint.
    """
    transaction.validate()
    symbol = transaction.asset.symbol_or_name()
    counterparty = transaction.counterparty_name or 'unknown counterparty'
    reference = f' with reference: {transaction.reference}' if transaction.reference else ''
    if transaction.side == BankTransactionSide.CREDIT:
        event_type, event_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.NONE
        notes = f'Receive {transaction.amount} {symbol} from {counterparty}{reference}'
    elif transaction.kind == BankTransactionKind.FEE:
        event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.FEE
        notes = f'Pay {transaction.amount} {symbol} as {location!s} fee{reference}'
    else:
        event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.NONE
        notes = f'Send {transaction.amount} {symbol} to {counterparty}{reference}'

    extra_data: BankTransactionExtraData = {
        'bank_account_id': transaction.account_id,
        'kind': transaction.kind.serialize(),
    }
    if transaction.counterparty_account is not None:
        extra_data['counterparty_account'] = transaction.counterparty_account
    if transaction.reference is not None:
        extra_data['reference'] = transaction.reference

    return [BankTransactionEvent(
        group_identifier=create_group_identifier_from_unique_id(
            location=location,
            unique_id=transaction.source_id,
        ),
        sequence_index=0,
        timestamp=transaction.timestamp,
        location=location,
        location_label=location_label,
        event_type=event_type,
        event_subtype=event_subtype,
        asset=transaction.asset,
        amount=transaction.amount,
        notes=notes,
        extra_data=extra_data,
    )]
