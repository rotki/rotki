import logging
from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import (
    CPT_KINETIQ,
    INSTANT_UNSTAKE_EXECUTED_TOPIC,
    KINETIQ_CPT_DETAILS,
    KINETIQ_STAKING_MANAGERS,
    REDELEGATION_REQUESTED_TOPIC,
    STAKE_RECEIVED_TOPIC,
    WITHDRAWAL_CONFIRMED_TOPIC,
    WITHDRAWAL_QUEUED_TOPIC,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KinetiqDecoder(EvmDecoderInterface):
    """Decoder for the Kinetiq liquid staking protocol on hyperliquid

    Users stake native HYPE via a StakingManager and receive its LST (kHYPE for the
    flagship deployment, flowHYPE/HiHYPE/asxnHYPE/hylqHYPE for the institutional
    partner deployments which run the same contract). Unstaking happens either through
    the withdrawal queue (queueWithdrawal + confirmWithdrawal after the withdrawal
    delay) or instantly against the buffer for a fee.
    """

    def _decode_stake(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode staking native HYPE for the staking manager's LST"""
        if not self.base.is_tracked(staker := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        lst_token_id = KINETIQ_STAKING_MANAGERS[context.tx_log.address]
        hype_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_HYPE and
                    event.amount == hype_amount and
                    event.location_label == staker
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Stake {hype_amount} HYPE in Kinetiq'
                event.counterparty = CPT_KINETIQ
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == lst_token_id and
                    event.location_label == staker and
                    event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.amount} {event.asset.resolve_to_evm_token().symbol} from staking in Kinetiq'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                in_event = event

        if out_event is None or in_event is None:
            log.error('Failed to find the HYPE spend and LST receive events for Kinetiq stake', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_queue_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode queueing an LST withdrawal from the staking manager"""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        lst_token_id = KINETIQ_STAKING_MANAGERS[context.tx_log.address]
        withdrawal_id = int.from_bytes(context.tx_log.topics[3])
        lst_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        hype_amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == lst_token_id and
                    event.amount == lst_amount and
                    event.location_label == user and
                    event.address == context.tx_log.address
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Queue unstaking of {lst_amount} {event.asset.resolve_to_evm_token().symbol} for {hype_amount} HYPE from Kinetiq with withdrawal request id {withdrawal_id}'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                event.extra_data = {'withdrawal_id': withdrawal_id}
                break
        else:
            log.error('Failed to find the LST transfer event for Kinetiq queued withdrawal', transaction=context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_confirm_withdrawal(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode confirming a queued withdrawal and receiving the unstaked HYPE.

        Multiple withdrawal requests can be confirmed in a single transaction but the
        HYPE is sent to the user in a single internal transaction, so the receive event
        is transformed only once, keeping its total amount.
        """
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_HYPE and
                    event.location_label == user and
                    event.address == context.tx_log.address
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Unstake {event.amount} HYPE from Kinetiq'
                event.counterparty = CPT_KINETIQ
                break
        else:  # can happen for the second and later confirmations of a batch
            if int.from_bytes(context.tx_log.data[:32]) != 0:  # only log if HYPE was expected
                found_transformed = any(
                    event.counterparty == CPT_KINETIQ and
                    event.event_type == HistoryEventType.WITHDRAWAL
                    for event in context.decoded_events
                )
                if not found_transformed:
                    log.error('Failed to find the HYPE receive event for Kinetiq confirmed withdrawal', transaction=context.transaction)  # noqa: E501

        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_instant_unstake(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode instantly unstaking the LST for HYPE against the buffer for a fee"""
        if not self.base.is_tracked(user := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        lst_token_id = KINETIQ_STAKING_MANAGERS[context.tx_log.address]
        lst_amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        hype_amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        in_event, out_event = None, None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset.identifier == lst_token_id and
                    event.amount == lst_amount and
                    event.location_label == user and
                    event.address == context.tx_log.address
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Instantly unstake {lst_amount} {event.asset.resolve_to_evm_token().symbol} from Kinetiq'  # noqa: E501
                event.counterparty = CPT_KINETIQ
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_HYPE and
                    event.amount == hype_amount and
                    event.location_label == user
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Receive {hype_amount} HYPE from unstaking in Kinetiq'
                event.counterparty = CPT_KINETIQ
                in_event = event

        if out_event is None or in_event is None:
            log.error('Failed to find the LST spend and HYPE receive events for Kinetiq instant unstake', transaction=context.transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KINETIQ)

    def _decode_redelegation(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a validator redelegation request. This is an operator action moving
        delegated HYPE between hypercore validators and moves no user funds."""
        if not self.base.is_tracked(sender := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_validator = bytes_to_address(context.tx_log.topics[2])
        to_validator = bytes_to_address(context.tx_log.topics[3])
        amount = from_wei(int.from_bytes(context.tx_log.data[:32]))
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_HYPE,
            amount=amount,
            location_label=sender,
            notes=f'Request redelegation of {amount} HYPE from validator {from_validator} to validator {to_validator} in Kinetiq',  # noqa: E501
            counterparty=CPT_KINETIQ,
            address=context.tx_log.address,
        )
        return EvmDecodingOutput(events=[event])

    def _decode_staking_manager_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == STAKE_RECEIVED_TOPIC:
            return self._decode_stake(context)
        if context.tx_log.topics[0] == WITHDRAWAL_QUEUED_TOPIC:
            return self._decode_queue_withdrawal(context)
        if context.tx_log.topics[0] == WITHDRAWAL_CONFIRMED_TOPIC:
            return self._decode_confirm_withdrawal(context)
        if context.tx_log.topics[0] == INSTANT_UNSTAKE_EXECUTED_TOPIC:
            return self._decode_instant_unstake(context)
        if context.tx_log.topics[0] == REDELEGATION_REQUESTED_TOPIC:
            return self._decode_redelegation(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(
            KINETIQ_STAKING_MANAGERS,
            (self._decode_staking_manager_events,),
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (KINETIQ_CPT_DETAILS,)
