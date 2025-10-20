import logging
from abc import ABC
from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.chain.ethereum.constants import ETH2_DEPOSIT_ADDRESS
from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    CPT_ETH2,
    MAX_EFFECTIVE_BALANCE,
    MIN_EFFECTIVE_BALANCE,
    UNKNOWN_VALIDATOR_INDEX,
)
from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorType
from rotkehlchen.chain.ethereum.modules.eth2.utils import form_withdrawal_notes
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address, deserialize_fval
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EVMTxHash,
    FVal,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)

from .base import HISTORY_EVENT_DB_TUPLE_WRITE, HistoryBaseEntry, HistoryBaseEntryType
from .evm_event import EvmEvent
from .onchain_event import CHAIN_EVENT_FIELDS_TYPE

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

ETH_STAKING_EVENT_DB_TUPLE_READ = tuple[
    int,            # identifier
    str,            # event_identifier
    int,            # sequence_index
    int,            # timestamp
    str | None,  # location label
    str,            # amount
    str,            # event_subtype
    dict[str, Any] | None,  # extra data
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
    str,            # notes
    bytes,          # tx_hash
    int,            # validator_index
]

STAKING_DB_INSERT_QUERY_STR = 'eth_staking_events_info(identifier, validator_index, is_exit_or_blocknumber) VALUES (?, ?, ?)'  # noqa: E501
STAKING_DB_UPDATE_QUERY_STR = 'UPDATE eth_staking_events_info SET validator_index=?, is_exit_or_blocknumber=?'  # noqa: E501


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthStakingEvent(HistoryBaseEntry, ABC):  # noqa: PLW1641  # hash in superclass
    """An ETH staking related event. Block production/withdrawal"""

    def __init__(
            self,
            event_identifier: str,
            sequence_index: int,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            validator_index: int,
            timestamp: TimestampMS,
            amount: FVal,
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
            amount=amount,
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
            amount: FVal,
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
            amount=amount,
            location_label=withdrawal_address,
            is_exit_or_blocknumber=is_exit,
            notes=form_withdrawal_notes(is_exit=is_exit, validator_index=validator_index, amount=amount),  # noqa: E501
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
        entry = cast('ETH_STAKING_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[5], 'amount', 'eth withdrawal event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            timestamp=TimestampMS(entry[3]),
            amount=amount,
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
            amount=base_data['amount'],
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
        with accounting.database.conn.read_ctx() as cursor:
            validator_info = accounting.dbeth2.get_validators_with_status(
                cursor=cursor,
                validator_indices={self.validator_index},
            )[0]

        event_ts, is_exit = self.get_timestamp_in_sec(), self.is_exit_or_blocknumber != 0
        name = 'Exit' if is_exit else 'Withdrawal'
        if validator_info.validator_type != ValidatorType.ACCUMULATING:
            profit_or_loss_amount = self.amount  # distributing validators, all of the withdrawal is profit  # noqa: E501

            # Note: This doesn't correctly handle validators with >32 ETH initial deposits, where
            # the first withdrawal might include both excess principal and possible rewards.
            #
            # handles both kinds of exits (profit if > 32 ETH) or (loss if < 32 ETH)
            if self.amount >= MIN_EFFECTIVE_BALANCE or is_exit:
                profit_or_loss_amount = self.amount - MIN_EFFECTIVE_BALANCE

        elif is_exit:  # Accumulating validator exit
            if (profit_or_loss_amount := max(ZERO, self.amount - MAX_EFFECTIVE_BALANCE)) == ZERO:
                # If no profit detected, then it is a loss and equals total deposited - total withdrawn(just before this event)  # noqa: E501
                balances, _, _ = accounting.dbeth2.process_accumulating_validators_balances_and_pnl(  # noqa: E501
                    from_ts=Timestamp(0),
                    to_ts=Timestamp(event_ts - 1),
                    validator_indices=[self.validator_index],
                    balances_over_time=defaultdict(lambda: defaultdict(lambda: ZERO)),
                    withdrawals_pnl=defaultdict(lambda: ZERO),
                    exits_pnl=defaultdict(lambda: ZERO),
                )
                if len(validator_balances := list(balances[self.validator_index].values())) == 0 or validator_balances[-1] < self.amount:  # noqa: E501
                    log.error(
                        f'Validator {self.validator_index} has an unexpected last balance ({validator_balances[-1]}) '  # noqa: E501
                        f'less than exit amount ({self.amount}) for {self}. Using zero as amount',
                    )
                    profit_or_loss_amount = ZERO
                else:
                    profit_or_loss_amount = -FVal(validator_balances[-1] - self.amount)
        else:  # Accumulating validator withdrawal (partial or skimming)
            _, withdrawal_pnl, _ = accounting.dbeth2.process_accumulating_validators_balances_and_pnl(  # noqa: E501
                from_ts=event_ts,
                to_ts=event_ts,
                validator_indices=[self.validator_index],
                balances_over_time=defaultdict(lambda: defaultdict(lambda: ZERO)),
                withdrawals_pnl=defaultdict(lambda: ZERO),
                exits_pnl=defaultdict(lambda: ZERO),
            )
            profit_or_loss_amount = withdrawal_pnl.get(self.validator_index, ZERO)

        if profit_or_loss_amount > ZERO:
            notes = f'{name} of {self.amount} ETH from validator {self.validator_index}'
            if self.amount != profit_or_loss_amount:  # this happens with validator exits and accumulating validator withdrawals  # noqa: E501
                notes += f'. Only {profit_or_loss_amount} is profit'

            accounting.add_in_event(
                event_type=AccountingEventType.HISTORY_EVENT,
                notes=notes,
                location=self.location,
                timestamp=event_ts,
                asset=self.asset,
                amount=profit_or_loss_amount,
                taxable=accounting.events_accountant.rules_manager.eth_staking_taxable_after_withdrawal_enabled,
            )
        else:
            accounting.add_out_event(
                event_type=AccountingEventType.HISTORY_EVENT,
                notes=f'Exit of {self.amount} ETH from validator {self.validator_index}. Loss of {profit_or_loss_amount} incurred',  # noqa: E501
                location=self.location,
                timestamp=event_ts,
                asset=self.asset,
                amount=abs(profit_or_loss_amount),
                taxable=accounting.events_accountant.rules_manager.eth_staking_taxable_after_withdrawal_enabled,
            )
        return 1


class EthBlockEvent(EthStakingEvent):
    """An ETH block production/MEV event

    These events have a kind of special meaning based on type/subtype and sequence index.
    0 -> Normal block production. This contains the fee recipient event. May or may
    not be a tracked address
    1 -> MEV event. This contains the MEV reported by the relayer (we get this from beaconcha.in).
    This may not be the actual true amount received by the mev recipient. Sometimes they mistakenly
    add the fee amount in too if the fee is also received by the same address or the amount
    is simply wrong.

    -----

    Even though they are EVM history events and not block events, by changing their event
    identifier to be same as the blocks we move the MEV receivals here with sequence
    index 2 and higher.

    2 ++ -> We move here all the actual MEV transfers to the fee recipient. As there can be
    multiple ones, this is what we must count as the actual MEV reported. Also we should not trust
    what the relayer (seq index 1) is reporting. Only what we verify we received.
    """

    def __init__(
            self,
            validator_index: int,
            timestamp: TimestampMS,
            amount: FVal,
            fee_recipient: ChecksumEvmAddress,
            fee_recipient_tracked: bool,
            block_number: int,
            is_mev_reward: bool,
            identifier: int | None = None,
            event_identifier: str | None = None,
    ) -> None:

        if is_mev_reward:
            sequence_index = 1
            event_type = HistoryEventType.INFORMATIONAL  # the Relayer reported MEV is always info
            event_subtype = HistoryEventSubType.MEV_REWARD
            notes = f'Validator {validator_index} produced block {block_number}. Relayer reported {amount} ETH as the MEV reward going to {fee_recipient}'  # noqa: E501
        else:
            sequence_index = 0
            event_type = HistoryEventType.STAKING if fee_recipient_tracked else HistoryEventType.INFORMATIONAL  # noqa: E501
            event_subtype = HistoryEventSubType.BLOCK_PRODUCTION
            notes = f'Validator {validator_index} produced block {block_number} with {amount} ETH going to {fee_recipient} as the block reward'  # noqa: E501

        super().__init__(
            identifier=identifier,
            event_identifier=self.form_event_identifier(block_number) if event_identifier is None else event_identifier,  # noqa: E501
            sequence_index=sequence_index,
            timestamp=timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            validator_index=validator_index,
            amount=amount,
            location_label=fee_recipient,
            is_exit_or_blocknumber=block_number,
            notes=notes,
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
    def deserialize_from_db(cls: type['EthBlockEvent'], entry: tuple, fee_recipient_tracked: bool) -> 'EthBlockEvent':  # type: ignore[override]  # noqa: E501
        """
        We have an annoying typing problem here. We are breaking the Liskov principle by adding an
        extra argument to the subclass function. But not sure what else to do since we need it.
        Mypy will stop complaining if we make it optional but not sure what to put as default
        value in that case. This here and in the deserialize() function needs some more thinking
        """
        entry = cast('ETH_STAKING_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[5], 'amount', 'eth block event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            timestamp=TimestampMS(entry[3]),
            amount=amount,
            fee_recipient=entry[4],  # type: ignore  # exists for these events
            fee_recipient_tracked=fee_recipient_tracked,
            validator_index=entry[8],
            block_number=entry[9],
            is_mev_reward=entry[6] == HistoryEventSubType.MEV_REWARD.serialize(),
        )

    @classmethod
    def deserialize(cls: type['EthBlockEvent'], data: dict[str, Any], fee_recipient_tracked: bool) -> 'EthBlockEvent':  # type: ignore[override]  # noqa: E501
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
            amount=base_data['amount'],
            validator_index=validator_index,
            fee_recipient=fee_recipient,
            fee_recipient_tracked=fee_recipient_tracked,
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

        if self.event_type != HistoryEventType.STAKING or self.location_label not in accounts.eth:
            return 1  # fee recipient not tracked or mev relay info. So do not add it in accounting

        assert self.event_subtype == HistoryEventSubType.BLOCK_PRODUCTION, 'Only block production events should come here'  # Because MEV rewards are always information and actual MEV comes in as transaction events # noqa: E501
        accounting.add_in_event(
            event_type=AccountingEventType.HISTORY_EVENT,
            notes=f'Block reward of {self.amount} for block {self.is_exit_or_blocknumber}',
            location=self.location,
            timestamp=self.get_timestamp_in_sec(),
            asset=self.asset,
            amount=self.amount,
            taxable=True,
        )
        return 1


class EthDepositEvent(EvmEvent, EthStakingEvent):  # noqa: PLW1641  # hash in superclass
    """An ETH deposit event"""

    def __init__(
            self,
            tx_ref: EVMTxHash,
            validator_index: int,
            sequence_index: int,
            timestamp: TimestampMS,
            amount: FVal,
            depositor: ChecksumEvmAddress,
            extra_data: dict[str, Any] | None = None,
            identifier: int | None = None,
            event_identifier: str | None = None,
    ) -> None:
        suffix = f'{validator_index}' if validator_index != UNKNOWN_VALIDATOR_INDEX else 'with a not yet known validator index'  # noqa: E501
        super().__init__(  # super should call evm event
            tx_ref=tx_ref,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            amount=amount,
            location_label=depositor,
            notes=f'Deposit {amount} ETH to validator {suffix}',
            counterparty=CPT_ETH2,
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
        return f'EthDepositEvent({self.validator_index=}, {self.timestamp=}, {self.tx_ref=})'

    def __eq__(self, other: object) -> bool:
        return (
            EvmEvent.__eq__(self, other) is True and
            EthStakingEvent.__eq__(self, other) is True
        )

    def serialize_for_db(self) -> tuple[  # type: ignore  # wont match EvmEvent supertype
            tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE],
            tuple[str, str, CHAIN_EVENT_FIELDS_TYPE],
            tuple[str, str, tuple[int, int]],
    ]:
        base_tuple, chain_tuple = self._serialize_onchain_event_tuple_for_db()
        return (
            base_tuple,
            chain_tuple,
            (STAKING_DB_INSERT_QUERY_STR, STAKING_DB_UPDATE_QUERY_STR, (self.validator_index, 0)),
        )

    def serialize(self) -> dict[str, Any]:
        return super().serialize() | {'validator_index': self.validator_index}

    @classmethod
    def deserialize_from_db(cls: type['EthDepositEvent'], entry: tuple) -> 'EthDepositEvent':
        entry = cast('EVM_DEPOSIT_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[5], 'amount', 'eth deposit event')
        return cls(
            tx_ref=deserialize_evm_tx_hash(entry[7]),
            validator_index=entry[8],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            amount=amount,
            depositor=entry[4],  # type: ignore  # exists for these events
            identifier=entry[0],
            event_identifier=entry[1],
        )

    @classmethod
    def deserialize(cls: type['EthDepositEvent'], data: dict[str, Any]) -> 'EthDepositEvent':
        base_data = cls._deserialize_base_history_data(data)

        try:
            tx_ref = deserialize_evm_tx_hash(data['tx_ref'])
            validator_index = data['validator_index']
        except KeyError as e:
            raise DeserializationError(f'Could not find key {e!s} for EthDepositEvent') from e

        if not isinstance(validator_index, int):
            raise DeserializationError(f'Found non-int validator index {validator_index}')

        if base_data['location_label'] is None:
            raise DeserializationError('Did not provide location_label (depositor) address for Eth Deposit event')  # noqa: E501

        return cls(
            tx_ref=tx_ref,
            validator_index=validator_index,
            sequence_index=base_data['sequence_index'],
            timestamp=base_data['timestamp'],
            amount=base_data['amount'],
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
