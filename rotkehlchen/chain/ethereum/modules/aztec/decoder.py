import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi
from eth_utils import to_checksum_address

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    A_AZTEC,
    AZTEC_CPT_DETAILS,
    AZTEC_STAKING_DATA,
    AZTEC_TOKEN,
    AZTEC_TOKEN_ID,
    CPT_AZTEC,
    DELEGATE_CHANGED,
    GSE,
    GSE_DEPOSIT,
    PULL_SPLIT_FACTORY,
    SPLIT_CREATED,
    SPLIT_DISTRIBUTED,
    STAKED_WITH_PROVIDER,
    STAKING_REGISTRY,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import ActionItem
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(frozen=True)
class AztecStakingPosition:
    staker: ChecksumEvmAddress
    attester: ChecksumEvmAddress
    rollup: ChecksumEvmAddress
    split: ChecksumEvmAddress
    allocation: int
    total_allocation: int
    amount: FVal


class AztecDecoder(EvmDecoderInterface):
    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.aztec_token = A_AZTEC.resolve_to_evm_token()
        self.positions_by_attester: dict[ChecksumEvmAddress, AztecStakingPosition] = {}
        self.positions_by_split: dict[ChecksumEvmAddress, AztecStakingPosition] = {}
        self._load_staking_positions()

    def _remember_position(self, position: AztecStakingPosition) -> None:
        self.positions_by_attester[position.attester] = position
        self.positions_by_split[position.split] = position

    def _load_staking_positions(self) -> None:
        """Load position metadata saved on previously decoded staking events."""
        dbevents = DBHistoryEvents(self.base.database)
        db_filter = EvmEventFilterQuery.make(
            counterparties=[CPT_AZTEC],
            location=Location.ETHEREUM,
            type_and_subtype_combinations=[(
                HistoryEventType.STAKING,
                HistoryEventSubType.DEPOSIT_ASSET,
            )],
        )
        with self.base.database.conn.read_ctx() as cursor:
            events = dbevents.get_history_events_internal(cursor=cursor, filter_query=db_filter)

        for event in events:
            if (
                    event.location_label is None or
                    event.extra_data is None or
                    (data := event.extra_data.get(AZTEC_STAKING_DATA)) is None
            ):
                continue

            try:
                self._remember_position(AztecStakingPosition(
                    staker=string_to_evm_address(event.location_label),
                    attester=string_to_evm_address(data['attester']),
                    rollup=string_to_evm_address(data['rollup']),
                    split=string_to_evm_address(data['split']),
                    allocation=int(data['allocation']),
                    total_allocation=int(data['total_allocation']),
                    amount=event.amount,
                ))
            except (DeserializationError, KeyError, TypeError, ValueError) as e:
                log.error(
                    'Failed to load Aztec staking position from event %s due to %s', event, e,
                )

    @staticmethod
    def _position_extra_data(position: AztecStakingPosition) -> dict[str, dict[str, Any]]:
        return {AZTEC_STAKING_DATA: {
            'allocation': position.allocation,
            'attester': position.attester,
            'rollup': position.rollup,
            'split': position.split,
            'total_allocation': position.total_allocation,
        }}

    def _find_staked_amount(self, context: DecoderContext) -> FVal | None:
        for tx_log in context.all_logs:
            if (
                    tx_log.address == AZTEC_TOKEN and
                    len(tx_log.topics) == 3 and
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    bytes_to_address(tx_log.topics[2]) == STAKING_REGISTRY
            ):
                return token_normalized_value(
                    token_amount=int.from_bytes(tx_log.data),
                    token=self.aztec_token,
                )

        return None

    def _decode_stake(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != STAKED_WITH_PROVIDER:
            return DEFAULT_EVM_DECODING_OUTPUT

        split = bytes_to_address(context.tx_log.data[:32])
        for tx_log in context.all_logs:
            if (
                    tx_log.address == PULL_SPLIT_FACTORY and
                    tx_log.topics[0] == SPLIT_CREATED and
                    bytes_to_address(tx_log.topics[1]) == split
            ):
                split_params, _owner, _creator, _nonce = decode_abi(
                    ['(address[],uint256[],uint256,uint16)', 'address', 'address', 'uint256'],
                    tx_log.data,
                )
                recipients, allocations, total_allocation, _distribution_incentive = split_params
                allocation, staker_raw = max(zip(allocations, recipients, strict=True))
                staker = to_checksum_address(staker_raw)
                break
        else:
            log.error(
                'Could not find Aztec reward split creation in %s', context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(staker):
            return DEFAULT_EVM_DECODING_OUTPUT
        if allocation * 2 <= total_allocation:
            log.error('Could not identify the majority recipient of Aztec split %s', split)
            return DEFAULT_EVM_DECODING_OUTPUT
        if (amount := self._find_staked_amount(context)) is None:
            log.error(
                'Could not find the AZTEC staking transfer in %s', context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        position = AztecStakingPosition(
            staker=staker,
            attester=bytes_to_address(context.tx_log.topics[3]),
            rollup=bytes_to_address(context.tx_log.topics[2]),
            split=split,
            allocation=allocation,
            total_allocation=total_allocation,
            amount=amount,
        )
        self._remember_position(position)
        extra_data = self._position_extra_data(position)
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == AZTEC_TOKEN_ID and
                    event.amount == amount and
                    event.location_label == staker
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Stake {amount} AZTEC with Aztec provider {int.from_bytes(context.tx_log.topics[1])}'  # noqa: E501
                event.counterparty = CPT_AZTEC
                event.address = STAKING_REGISTRY
                event.extra_data = extra_data
                return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=self.aztec_token,
            amount=amount,
            location_label=staker,
            notes=f'Stake {amount} AZTEC with Aztec provider {int.from_bytes(context.tx_log.topics[1])}',  # noqa: E501
            counterparty=CPT_AZTEC,
            address=STAKING_REGISTRY,
            extra_data=extra_data,
        )])

    def _decode_gse_event(self, context: DecoderContext) -> EvmDecodingOutput:
        topic = context.tx_log.topics[0]
        if topic == GSE_DEPOSIT:
            attester = bytes_to_address(context.tx_log.topics[2])
            if (position := self.positions_by_attester.get(attester)) is None:
                return DEFAULT_EVM_DECODING_OUTPUT

            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.GOVERNANCE,
                asset=self.aztec_token,
                amount=ZERO,
                location_label=position.staker,
                notes=f'Register {position.amount} AZTEC stake for Aztec governance with attester {attester}',  # noqa: E501
                counterparty=CPT_AZTEC,
                address=GSE,
            )])

        if topic != DELEGATE_CHANGED:
            return DEFAULT_EVM_DECODING_OUTPUT

        attester = bytes_to_address(context.tx_log.topics[1])
        old_delegate = bytes_to_address(context.tx_log.data[:32])
        new_delegate = bytes_to_address(context.tx_log.data[32:64])
        if (
                ZERO_ADDRESS in (old_delegate, new_delegate) or
                (position := self.positions_by_attester.get(attester)) is None
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.aztec_token,
            amount=ZERO,
            location_label=position.staker,
            notes=f'Change Aztec governance delegate for attester {attester} from {old_delegate} to {new_delegate}',  # noqa: E501
            counterparty=CPT_AZTEC,
            address=GSE,
        )])

    def _decode_split_distribution(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
            strict: bool = False,  # pylint: disable=unused-argument
    ) -> EvmDecodingOutput:
        context = DecoderContext(
            tx_log=tx_log,
            transaction=transaction,
            decoded_events=decoded_events,
            action_items=action_items,
            all_logs=all_logs,
        )
        if (
                context.tx_log.topics[0] != SPLIT_DISTRIBUTED or
                bytes_to_address(context.tx_log.topics[1]) != AZTEC_TOKEN or
                (position := self.positions_by_split.get(context.tx_log.address)) is None
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount_raw = int.from_bytes(context.tx_log.data) * position.allocation // position.total_allocation  # noqa: E501
        amount = token_normalized_value(token_amount=amount_raw, token=self.aztec_token)
        if amount == ZERO:
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=self.aztec_token,
            amount=amount,
            location_label=position.staker,
            notes=f'Receive {amount} AZTEC staking rewards',
            counterparty=CPT_AZTEC,
            address=context.tx_log.address,
        )])

    def decoding_rules(self) -> list[Callable]:
        return [self._decode_split_distribution]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GSE: (self._decode_gse_event,),
            STAKING_REGISTRY: (self._decode_stake,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (AZTEC_CPT_DETAILS,)
