from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Optional, cast

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_fval
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS

from .balance import Balance

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

from rotkehlchen.constants.assets import A_ETH

from .base import HISTORY_EVENT_DB_TUPLE_WRITE, HistoryBaseEntry, HistoryBaseEntryType

WITHDRAWAL_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    int,            # timestamp
    Optional[str],  # location label
    str,            # amount
    str,            # usd value
    int,            # validator_index
    bool,           # is_exit
]


class EthWithdrawalEvent(HistoryBaseEntry):
    """An ETH Withdrawal event"""

    def __init__(
            self,
            validator_index: int,
            timestamp: TimestampMS,
            balance: Balance,
            withdrawal_address: ChecksumEvmAddress,
            is_exit: bool,
            identifier: Optional[int] = None,
    ) -> None:
        self.validator_index = validator_index
        self.is_exit = is_exit
        super().__init__(
            event_identifier=f'eth2_withdrawal_{validator_index}_{timestamp}'.encode(),
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=balance,
            location_label=withdrawal_address,
            notes=f'Withdrew {balance.amount} ETH from validator {validator_index}',
        )

    def __repr__(self) -> str:
        return f'WithdrawalEvent({self.validator_index=}, {self.timestamp=}, {self.is_exit=})'

    def serialize_for_db(self) -> tuple[HISTORY_EVENT_DB_TUPLE_WRITE, tuple[int, int]]:
        base_tuple = self._serialize_base_tuple_for_db(HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT)
        return (base_tuple, (self.validator_index, int(self.is_exit)))

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {'validator_index': self.validator_index, 'is_exit': self.is_exit}  # noqa: E501

    @classmethod
    def deserialize_from_db(cls: type['EthWithdrawalEvent'], entry: tuple) -> 'EthWithdrawalEvent':
        entry = cast(WITHDRAWAL_EVENT_DB_TUPLE_READ, entry)
        amount = deserialize_fval(entry[3], 'amount', 'eth withdrawal event')
        usd_value = deserialize_fval(entry[4], 'usd_value', 'eth withdrawal event')
        return cls(
            identifier=entry[0],
            timestamp=TimestampMS(entry[1]),
            balance=Balance(amount, usd_value),
            withdrawal_address=entry[2],  # type: ignore  # exists for these events
            validator_index=entry[5],
            is_exit=bool(entry[6]),
        )

    @property
    def serialized_event_identifier(self) -> str:
        return self.event_identifier.decode()

    @classmethod
    def deserialize_event_identifier(cls: type['EthWithdrawalEvent'], val: str) -> bytes:
        return val.encode()

    @classmethod
    def deserialize(cls: type['EthWithdrawalEvent'], data: dict[str, Any]) -> 'EthWithdrawalEvent':
        base_data = cls._deserialize_base_history_data(data)
        try:
            validator_index = data['validator_index']
            withdrawal_address = deserialize_evm_address(data['withdrawal_address'])
            is_exit = data['is_exit']
        except KeyError as e:
            raise DeserializationError(f'Did not find expected withdrawal event key {str(e)}') from e  # noqa: E501

        if not isinstance(validator_index, int):
            raise DeserializationError(f'Found non-int validator index {validator_index}')

        return cls(
            timestamp=base_data['timestamp'],
            balance=base_data['balance'],
            validator_index=validator_index,
            withdrawal_address=withdrawal_address,
            is_exit=is_exit,
        )

    def __eq__(self, other: Any) -> bool:
        return (
            HistoryBaseEntry.__eq__(self, other) is True and
            self.validator_index == other.validator_index
        )

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_EVENT

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
        return False  # TODO: Same question on ignoring as general HistoryEvent

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        profit_amount = self.balance.amount
        if self.balance.amount >= 32:
            profit_amount = 32 - self.balance.amount

        # TODO: This is really hacky. We can and should combine deposit and withdrawal processing
        # by querying deposits for that validator index. Which requires
        # saving pubkey and validator index for deposits.

        accounting.add_acquisition(
            event_type=AccountingEventType.HISTORY_EVENT,
            notes=f'Withdrawal of {self.balance.amount} ETH from validator {self.validator_index}. Only {profit_amount} is profit',  # noqa: E501
            location=self.location,
            timestamp=self.get_timestamp_in_sec(),
            asset=self.asset,
            amount=profit_amount,
            taxable=True,
        )
        return 1
