from abc import ABCMeta
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.constants import ETH2_DEPOSIT_ADDRESS
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2, UNKNOWN_VALIDATOR_INDEX
from rotkehlchen.chain.ethereum.modules.eth2.utils import form_withdrawal_notes
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_fval
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

from .evm_event import EvmProduct

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

from rotkehlchen.constants.assets import A_ETH

from .base import HISTORY_EVENT_DB_TUPLE_WRITE, HistoryBaseEntry, HistoryBaseEntryType
from .evm_event import EVM_EVENT_FIELDS, EvmEvent

ETH_STAKING_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str | None,  # location label
    str,            # amount
    str,            # usd value
    str,            # event_subtype
    int,            # validator_index
    int,            # is_exit_or_blocknumber
]

EVM_DEPOSIT_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str,            # depositor
    str,            # amount
    str,            # usd value
    bytes,          # tx_hash
    int,            # validator_index
]

STAKING_DB_INSERT_QUERY_STR = 'eth_staking_events_info(identifier, validator_index, is_exit_or_blocknumber) VALUES (?, ?, ?)'  # noqa: E501
STAKING_DB_UPDATE_QUERY_STR = 'UPDATE eth_staking_events_info SET validator_index=?, is_exit_or_blocknumber=?'  # noqa: E501


class EthStakingEvent(HistoryBaseEntry, metaclass=ABCMeta):  # noqa: PLW1641  # hash in superclass
    """An ETH staking related event. Block production/withdrawal"""

    def __init__(
            self,
            event_identifier: str,
            sequence_index: int,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            validator_index: int,
            timestamp: TimestampMS,
            balance: Balance,
            location_label: ChecksumEvmAddress,
            is_exit_or_blocknumber: int,
            notes: str,
            identifier: int | None = None,
    ) -> None:
        self.validator_index = validator_index
        self.is_exit_or_blocknumber = is_exit_or_blocknumber
        super().__init__(
            identifier=identifier,
            event_identifier=event_identifier,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=A_ETH,
            balance=balance,
            location_label=location_label,
            notes=notes,
        )

    def __eq__(self, other: object) -> bool:
        return (  # ignores are due to object and type checks in super not recognized
            HistoryBaseEntry.__eq__(self, other) is True and
            self.validator_index == other.validator_index and  # type: ignore
            self.is_exit_or_blocknumber == other.is_exit_or_blocknumber  # type: ignore
        )

    def _serialize_staking_tuple_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, tuple[int, int]],
    ]:
        return (
            self._serialize_base_tuple_for_db(),
            (
                STAKING_DB_INSERT_QUERY_STR,
                STAKING_DB_UPDATE_QUERY_STR,
                (self.validator_index, self.is_exit_or_blocknumber),
            ),
        )


class EthWithdrawalEvent(EthStakingEvent):
    """An ETH Withdrawal event"""

    def __init__(
            self,
            validator_index: int,
            timestamp: TimestampMS,
            balance: Balance,
            withdrawal_address: ChecksumEvmAddress,
            is_exit: bool,
            identifier: int | None = None,
            event_identifier: str | None = None,
    ) -> None:
        if event_identifier is None:
            # withdrawals happen at least every couple of days. For them to happen in the same
            # day for same validator we would need to drop to less than 115200 validators
            # https://ethereum.org/en/staking/withdrawals/#how-soon
            days = int(timestamp / 1000 / 86400)
            event_identifier = f'EW_{validator_index}_{days}'

        super().__init__(
            identifier=identifier,
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=timestamp,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            validator_index=validator_index,
            balance=balance,
            location_label=withdrawal_address,
            is_exit_or_blocknumber=is_exit,
            notes=form_withdrawal_notes(is_exit=is_exit, validator_index=validator_index, amount=balance.amount),  # noqa: E501
        )

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT

    def __repr__(self) -> str:
        return f'EthWithdrawalEvent({self.validator_index=}, {self.timestamp=}, is_exit={self.is_exit_or_blocknumber})'  # noqa: E501

    def serialize_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, tuple[int, int]],
    ]:
        return self._serialize_staking_tuple_for_db()

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {'validator_index': self.validator_index, 'is_exit': self.is_exit_or_blocknumber}  # noqa: E501

    @classmethod
    def deserialize_from_db(cls: type['EthWithdrawalEvent'], entry: tuple) -> 'EthWithdrawalEvent':
        entry = cast(ETH_STAKING_EVENT_DB_TUPLE_READ, entry)
        amount = deserialize_fval(entry[5], 'amount', 'eth withdrawal event')
        usd_value = deserialize_fval(entry[6], 'usd_value', 'eth withdrawal event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            timestamp=TimestampMS(entry[3]),
            balance=Balance(amount, usd_value),
            withdrawal_address=entry[4],  # type: ignore  # exists for these events
            validator_index=entry[8],
            is_exit=bool(entry[9]),
        )

    @classmethod
    def deserialize(cls: type['EthWithdrawalEvent'], data: dict[str, Any]) -> 'EthWithdrawalEvent':
        base_data = cls._deserialize_base_history_data(data)
        try:
            validator_index = data['validator_index']
            withdrawal_address = deserialize_evm_address(data['location_label'])
            is_exit = data['is_exit']
        except KeyError as e:
            raise DeserializationError(f'Did not find expected withdrawal event key {e!s}') from e

        if not isinstance(validator_index, int):
            raise DeserializationError(f'Found non-int validator index {validator_index}')

        return cls(
            timestamp=base_data['timestamp'],
            balance=base_data['balance'],
            validator_index=validator_index,
            withdrawal_address=withdrawal_address,
            is_exit=is_exit,
        )

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_EVENT

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        profit_amount = self.balance.amount
        if self.balance.amount >= 32:
            profit_amount = 32 - self.balance.amount

        # TODO: This is hacky and does not cover edge case where people mistakenly
        # double deposited for a validator. We can and should combine deposit and
        # withdrawal processing by querying deposits for that validator index.
        # saving pubkey and validator index for deposits.

        name = 'Exit' if bool(self.is_exit_or_blocknumber) else 'Withdrawal'
        accounting.add_in_event(
            event_type=AccountingEventType.HISTORY_EVENT,
            notes=f'{name} of {self.balance.amount} ETH from validator {self.validator_index}. Only {profit_amount} is profit',  # noqa: E501
            location=self.location,
            timestamp=self.get_timestamp_in_sec(),
            asset=self.asset,
            amount=profit_amount,
            taxable=True,
        )
        return 1


class EthBlockEvent(EthStakingEvent):
    """An ETH block production/MEV event"""

    def __init__(
            self,
            validator_index: int,
            timestamp: TimestampMS,
            balance: Balance,
            fee_recipient: ChecksumEvmAddress,
            block_number: int,
            is_mev_reward: bool,
            identifier: int | None = None,
            event_identifier: str | None = None,
    ) -> None:

        if is_mev_reward:
            sequence_index = 1
            event_subtype = HistoryEventSubType.MEV_REWARD
            name = 'mev reward'
        else:
            sequence_index = 0
            event_subtype = HistoryEventSubType.BLOCK_PRODUCTION
            name = 'block reward'

        super().__init__(
            identifier=identifier,
            event_identifier=self.form_event_identifier(block_number) if event_identifier is None else event_identifier,  # noqa: E501
            sequence_index=sequence_index,
            timestamp=timestamp,
            event_type=HistoryEventType.STAKING,
            event_subtype=event_subtype,
            validator_index=validator_index,
            balance=balance,
            location_label=fee_recipient,
            is_exit_or_blocknumber=block_number,
            notes=f'Validator {validator_index} produced block {block_number} with {balance.amount} ETH going to {fee_recipient} as the {name}',  # noqa: E501
        )

    @staticmethod
    def form_event_identifier(block_number: int) -> str:
        return f'BP1_{block_number}'

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.ETH_BLOCK_EVENT

    def __repr__(self) -> str:
        return f'EthBlockEvent({self.validator_index=}, {self.timestamp=}, block_number={self.is_exit_or_blocknumber}, {self.event_subtype=})'  # noqa: E501

    def serialize_for_db(self) -> tuple[
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, tuple[int, int]],
    ]:
        return self._serialize_staking_tuple_for_db()

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {'validator_index': self.validator_index, 'block_number': self.is_exit_or_blocknumber}  # noqa: E501

    @classmethod
    def deserialize_from_db(cls: type['EthBlockEvent'], entry: tuple) -> 'EthBlockEvent':
        entry = cast(ETH_STAKING_EVENT_DB_TUPLE_READ, entry)
        amount = deserialize_fval(entry[5], 'amount', 'eth block event')
        usd_value = deserialize_fval(entry[6], 'usd_value', 'eth block event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            timestamp=TimestampMS(entry[3]),
            balance=Balance(amount, usd_value),
            fee_recipient=entry[4],  # type: ignore  # exists for these events
            validator_index=entry[8],
            block_number=entry[9],
            is_mev_reward=entry[7] == HistoryEventSubType.MEV_REWARD.serialize(),
        )

    @classmethod
    def deserialize(cls: type['EthBlockEvent'], data: dict[str, Any]) -> 'EthBlockEvent':
        base_data = cls._deserialize_base_history_data(data)
        try:
            validator_index = data['validator_index']
            fee_recipient = deserialize_evm_address(data['location_label'])
            block_number = data['block_number']
        except KeyError as e:
            raise DeserializationError(f'Did not find expected eth block event key {e!s}') from e

        if not isinstance(validator_index, int):
            raise DeserializationError(f'Found non-int validator index {validator_index}')

        return cls(
            timestamp=base_data['timestamp'],
            balance=base_data['balance'],
            validator_index=validator_index,
            fee_recipient=fee_recipient,
            block_number=block_number,
            is_mev_reward=base_data['event_subtype'] == HistoryEventSubType.MEV_REWARD.serialize(),
        )

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_EVENT

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        """
        For block production events we should consume all 3 possible events directly here
        so that we do not double count anything
        """
        with accounting.database.conn.read_ctx() as cursor:
            accounts = accounting.database.get_blockchain_accounts(cursor)

        if self.location_label not in accounts.eth:
            return 1  # fee recipient not tracked. So we do not add it in accounting

        if self.event_subtype == HistoryEventSubType.MEV_REWARD:
            name = 'Mev reward'
        else:
            name = 'Block reward'

        accounting.add_in_event(
            event_type=AccountingEventType.HISTORY_EVENT,
            notes=f'{name} of {self.balance.amount} for block {self.is_exit_or_blocknumber}',
            location=self.location,
            timestamp=self.get_timestamp_in_sec(),
            asset=self.asset,
            amount=self.balance.amount,
            taxable=True,
        )
        return 1


class EthDepositEvent(EvmEvent, EthStakingEvent):  # noqa: PLW1641  # hash in superclass
    """An ETH deposit event"""

    def __init__(
            self,
            tx_hash: EVMTxHash,
            validator_index: int,
            sequence_index: int,
            timestamp: TimestampMS,
            balance: Balance,
            depositor: ChecksumEvmAddress,
            extra_data: dict[str, Any] | None = None,
            identifier: int | None = None,
            event_identifier: str | None = None,
    ) -> None:
        suffix = f'{validator_index}' if validator_index != UNKNOWN_VALIDATOR_INDEX else 'with a not yet known validator index'  # noqa: E501
        super().__init__(  # super should call evm event
            tx_hash=tx_hash,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=balance,
            location_label=depositor,
            notes=f'Deposit {balance.amount} ETH to validator {suffix}',
            counterparty=CPT_ETH2,
            product=EvmProduct.STAKING,
            address=ETH2_DEPOSIT_ADDRESS,
            identifier=identifier,
            event_identifier=event_identifier,
            extra_data=extra_data,
        )  # for EthStakingEvent, just do manually to not reassign all common ones
        self.validator_index = validator_index
        self.is_exit_or_blocknumber = 0

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.ETH_DEPOSIT_EVENT

    def __repr__(self) -> str:
        return f'EthDepositEvent({self.validator_index=}, {self.timestamp=}, {self.tx_hash=})'

    def __eq__(self, other: object) -> bool:
        return (
            EvmEvent.__eq__(self, other) is True and
            EthStakingEvent.__eq__(self, other) is True
        )

    def serialize_for_db(self) -> tuple[  # type: ignore  # wont match EvmEvent supertype
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, EVM_EVENT_FIELDS],
            tuple[str, str, tuple[int, int]],
    ]:
        base_tuple, evm_tuple = self._serialize_evm_event_tuple_for_db()
        return (
            base_tuple,
            evm_tuple,
            (STAKING_DB_INSERT_QUERY_STR, STAKING_DB_UPDATE_QUERY_STR, (self.validator_index, 0)),
        )

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {'validator_index': self.validator_index}

    @classmethod
    def deserialize_from_db(cls: type['EthDepositEvent'], entry: tuple) -> 'EthDepositEvent':
        entry = cast(EVM_DEPOSIT_EVENT_DB_TUPLE_READ, entry)
        amount = deserialize_fval(entry[5], 'amount', 'eth deposit event')
        usd_value = deserialize_fval(entry[6], 'usd_value', 'eth deposit event')
        return cls(
            tx_hash=deserialize_evm_tx_hash(entry[7]),
            validator_index=entry[8],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            balance=Balance(amount, usd_value),
            depositor=entry[4],  # type: ignore  # exists for these events
            identifier=entry[0],
            event_identifier=entry[1],
        )

    @classmethod
    def deserialize(cls: type['EthDepositEvent'], data: dict[str, Any]) -> 'EthDepositEvent':
        base_data = cls._deserialize_base_history_data(data)

        try:
            tx_hash = deserialize_evm_tx_hash(data['tx_hash'])
            validator_index = data['validator_index']
        except KeyError as e:
            raise DeserializationError(f'Could not find key {e!s} for EthDepositEvent') from e

        if not isinstance(validator_index, int):
            raise DeserializationError(f'Found non-int validator index {validator_index}')

        if base_data['location_label'] is None:
            raise DeserializationError('Did not provide location_label (depositor) address for Eth Deposit event')  # noqa: E501

        return cls(
            tx_hash=tx_hash,
            validator_index=validator_index,
            sequence_index=base_data['sequence_index'],
            timestamp=base_data['timestamp'],
            balance=base_data['balance'],
            depositor=deserialize_evm_address(base_data['location_label']),
            identifier=base_data['identifier'],
            event_identifier=base_data['event_identifier'],
        )

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.HISTORY_EVENT

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        """ETH staking deposits are not taxable"""
        return 1
