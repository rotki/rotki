from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

LOCK_4BYTE: Final = b'K\xbc\x17\n'
CLAIM_REWARD_4BYTE: Final = b'\xc6\xa0y`'
LOCK_ETHEREUM_AND_BASE_4BYTE: Final = b'(-?\xdf'

LOCKED_TOPIC: Final = b'\x9f\x1e\xc8\xc8\x80\xf7g\x98\xe7\xb7\x932]b^\x9b`\xe4\x08*U<\x98\xf4+l\xda6\x8d\xd6\x00\x08'  # noqa: E501
STAKED_TOPIC: Final = b'\x14I\xc6\xddxQ\xab\xc3\n\xbf7\xf5w\x15\xf4\x92\x01\x05\x19\x14|\xc2e/\xbc8 ,\x18\xa6\xee\x90'  # noqa: E501
DEPOSIT_AURA_BAL_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
REWARD_PAID_TOPIC: Final = b'\xe2@6@\xbah\xfe\xd3\xa2\xf8\x8buWU\x1d\x19\x93\xf8K\x99\xbb\x10\xff\x83?\x0c\xf8\xdb\x0c^\x04\x86'  # noqa: E501
DEPOSITED_TOPIC: Final = b's\xa1\x9d\xd2\x10\xf1\xa7\xf9\x02\x192\x14\xc0\xee\x91\xdd5\xee[M\x92\x0c\xba\x8dQ\x9e\xcae\xa7\xb4\x88\xca'  # noqa: E501

AURA_BAL_VAULT_ADDRESS = string_to_evm_address('0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9')
AURA_L2_BOOSTER_LITE_ADDRESS = string_to_evm_address('0x98Ef32edd24e2c92525E59afc4475C1242a30184')
AURA_ETHEREUM_BOOSTER_ADDRESS = string_to_evm_address('0xA57b8d98dAE62B26Ec3bcC4a365338157060B234')


class AuraFinanceCommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            claim_zap_address: ChecksumEvmAddress,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.claim_zap_address = claim_zap_address

    def _decode_lock_aura(self, context: DecoderContext) -> DecodingOutput:
        """Decodes locking AURA events on Ethereum and Base (vlAURA)."""
        locked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == locked_amount
            ):
                event.counterparty = CPT_AURA_FINANCE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Lock {locked_amount} {event.asset.resolve_to_asset_with_symbol().symbol} in auraLocker (vlAURA)'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_lock_aura_bridged(self, context: DecoderContext) -> DecodingOutput:
        """Decodes locking AURA events on bridged chains (excluding Ethereum)."""
        locked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        refund_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.evm_inquirer.native_token
            ):  # Refund event (if any) comes first
                refund_event = event
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.evm_inquirer.native_token
            ):
                event.counterparty = CPT_AURA_FINANCE
                event.event_subtype = HistoryEventSubType.FEE
                # Calculate bridge fee, accounting for potential refunds
                actual_bridge_fee = event.balance.amount if refund_event is None else event.balance.amount - refund_event.balance.amount  # noqa: E501
                event.balance.amount = actual_bridge_fee
                event.notes = f'Pay {actual_bridge_fee} {self.evm_inquirer.native_token.symbol} as bridge fee (to Ethereum)'  # noqa: E501
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == locked_amount and
                event.address == ZERO_ADDRESS
            ):
                event.counterparty = CPT_AURA_FINANCE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Lock {locked_amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Aura Finance (bridged)'  # noqa: E501

        if refund_event:  # Remove refund event; it's factored into the bridge fee
            context.decoded_events.remove(refund_event)

        return DEFAULT_DECODING_OUTPUT

    def _decode_reward_claims(self, context: DecoderContext) -> DecodingOutput:
        """Decodes Aura Finance reward claiming events."""
        if (
            context.tx_log.topics[0] != REWARD_PAID_TOPIC and
            context.transaction.to_address != self.claim_zap_address
        ):
            return DEFAULT_DECODING_OUTPUT

        recipient = bytes_to_address(context.tx_log.topics[1])
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient
            ):
                event.notes = f'Claim {event.balance.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Aura Finance'  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_AURA_FINANCE

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit_helper(
            self,
            context: DecoderContext,
            deposit_note_suffix: str,
            receive_note_suffix: str,
            received_amount:  FVal | None = None,
    ) -> DecodingOutput:
        """Helper function to decode deposit events where a wrapped token is received.

        Handles both the deposit and wrapped token receiving events. Used for
        auraBAL deposits and booster deposits.
        """
        receive_event = None
        deposit_events: list[EvmEvent] = []
        deposited_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            token = event.asset.resolve_to_asset_with_symbol()
            if (
                (received_amount is None or event.balance.amount == received_amount) and
                event.event_subtype == HistoryEventSubType.NONE and
                event.event_type == HistoryEventType.RECEIVE and
                event.address == ZERO_ADDRESS
            ):
                receive_event = event
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {received_amount or event.balance.amount} {token.symbol} {receive_note_suffix}'  # noqa: E501
                event.extra_data = {'deposit_events_num': len(deposit_events)}
                event.counterparty = CPT_AURA_FINANCE
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.balance.amount == deposited_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {deposited_amount} {token.symbol} {deposit_note_suffix}'
                event.counterparty = CPT_AURA_FINANCE
                deposit_events.append(event)

        maybe_reshuffle_events(
            events_list=context.decoded_events,
            ordered_events=deposit_events + [receive_event],
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit_aura_bal(self, context: DecoderContext) -> DecodingOutput:
        """Decodes auraBAL deposit events (Base, Arbitrum, Polygon)."""
        if context.tx_log.topics[0] != DEPOSIT_AURA_BAL_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        received_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return self._decode_deposit_helper(
            context=context,
            received_amount=received_amount,
            deposit_note_suffix='into auraBAL vault',
            receive_note_suffix='from auraBAL vault',
        )

    def _decode_booster_deposit(self, context: DecoderContext) -> DecodingOutput:
        """Decodes booster deposit events."""
        if context.tx_log.topics[0] != DEPOSITED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        return self._decode_deposit_helper(
            context=context,
            deposit_note_suffix='into an Aura gauge',
            receive_note_suffix='from an Aura gauge',
        )

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        if self.evm_inquirer.chain_id == ChainID.ETHEREUM:
            return {
                AURA_ETHEREUM_BOOSTER_ADDRESS: (self._decode_booster_deposit,),
            }

        return {
            AURA_BAL_VAULT_ADDRESS: (self._decode_deposit_aura_bal,),
            AURA_L2_BOOSTER_LITE_ADDRESS: (self._decode_booster_deposit,),
        }

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Callable]]:
        decoders = {CLAIM_REWARD_4BYTE: {REWARD_PAID_TOPIC: self._decode_reward_claims}}
        if self.evm_inquirer.chain_id in (ChainID.ETHEREUM, ChainID.BASE):
            decoders[LOCK_ETHEREUM_AND_BASE_4BYTE] = {STAKED_TOPIC: self._decode_lock_aura}
        if self.evm_inquirer.chain_id != ChainID.ETHEREUM:
            decoders[LOCK_4BYTE] = {LOCKED_TOPIC: self._decode_lock_aura_bridged}

        return decoders

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AURA_FINANCE,
            label='Aura Finance',
            image='aura_finance.svg'),
        )
