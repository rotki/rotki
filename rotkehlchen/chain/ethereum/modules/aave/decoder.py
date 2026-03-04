import logging
from typing import Any

from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    REWARDS_CLAIMED_TOPIC,
    STAKED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE, CPT_AAVE_V2
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_AAVE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    REDEEM_AAVE_OLD,
    REDEEM_TOPIC,
    REWARDS_CLAIMED,
    STAKED_AAVE,
    STK_AAVE_ADDR,
    STKAAVE_IDENTIFIER,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AaveDecoder(EvmDecoderInterface):
    """Aave decoder for staking and unstaking events"""
    def _decode_staking_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode aave staking unstaking events"""
        if context.tx_log.topics[0] in (STAKED_AAVE, STAKED_TOPIC):
            method = self._decode_stake
        elif context.tx_log.topics[0] in (REDEEM_TOPIC, REDEEM_AAVE_OLD):
            method = self._decode_unstake
        elif context.tx_log.topics[0] == REWARDS_CLAIMED:
            method = self._decode_rewards_claim
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        from_address = bytes_to_address(context.tx_log.topics[1])
        to_address = bytes_to_address(context.tx_log.topics[2])
        if not self.base.any_tracked([from_address, to_address]):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return method(from_address=from_address, to_address=to_address, amount=amount, context=context)  # noqa: E501

    def _decode_rewards_claim(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            amount: FVal,
            context: DecoderContext,
    ) -> EvmDecodingOutput:
        tracked_claimant = to_address if self.base.is_tracked(to_address) else from_address
        suffix = f' for {to_address}' if from_address != to_address and self.base.is_tracked(to_address) else ''  # noqa: E501
        claim_event = None
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_AAVE and
                    event.location_label == tracked_claimant and
                    event.amount == amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Claim {amount} AAVE from staking{suffix}'
                event.counterparty = CPT_AAVE
                event.address = STK_AAVE_ADDR
                claim_event = event
                break

        if claim_event is None:
            # A claim can be immediately re-staked in the same transaction so there is no
            # user-facing AAVE transfer to transform. Create the reward event from the claim log.
            claim_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.REWARD,
                asset=A_AAVE,
                amount=amount,
                location_label=tracked_claimant,
                notes=f'Claim {amount} AAVE from staking{suffix}',
                counterparty=CPT_AAVE,
                address=STK_AAVE_ADDR,
            )

        return EvmDecodingOutput(events=[claim_event] if claim_event not in context.decoded_events else None)  # noqa: E501

    def _decode_stake(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            amount: FVal,
            context: DecoderContext,
    ) -> EvmDecodingOutput:
        out_event, in_event = None, None
        claim_event = None
        suffix = f' for {to_address}' if from_address != to_address and self.base.is_tracked(from_address) else ''  # noqa: E501
        new_events = []
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == A_AAVE and
                    event.location_label == to_address and
                    event.amount == amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Stake {amount} AAVE'
                if from_address != to_address:
                    event.notes += f' for {to_address}'
                event.counterparty = CPT_AAVE
                out_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == STKAAVE_IDENTIFIER and
                event.location_label == to_address and
                event.amount == amount
            ):
                event.counterparty = CPT_AAVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.amount} stkAAVE from staking in Aave'
                in_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.REWARD and
                event.asset.identifier == STKAAVE_IDENTIFIER and
                event.location_label == to_address and
                event.amount == amount and
                event.counterparty == CPT_AAVE_V2
            ):
                # Older flows claim stkAAVE from v2 incentives and immediately stake it.
                # Normalize this into claim AAVE -> stake AAVE -> receive stkAAVE.
                claim_event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.STAKING,
                    event_subtype=HistoryEventSubType.REWARD,
                    asset=A_AAVE,
                    amount=amount,
                    location_label=to_address,
                    notes=f'Claim {amount} AAVE from staking{suffix}',
                    counterparty=CPT_AAVE,
                    address=STK_AAVE_ADDR,
                )
                event.counterparty = CPT_AAVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {event.amount} stkAAVE from staking in Aave'
                in_event = event
                new_events.append(claim_event)

        if out_event is None and in_event is not None:
            # A stake can use rewards claimed internally by the staking contract, so there may
            # be no user-facing AAVE spend transfer to transform. Create the stake event here.
            out_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_AAVE,
                amount=amount,
                location_label=to_address,
                notes=f'Stake {amount} AAVE{suffix}',
                counterparty=CPT_AAVE,
                address=STK_AAVE_ADDR,
            )
            new_events.append(out_event)

        if (
            claim_event is None and
            out_event is not None and
            any(
                len(log.topics) > 0 and log.topics[0] in {REWARDS_CLAIMED, REWARDS_CLAIMED_TOPIC}
                for log in context.all_logs
            ) and
            not any(
                event.event_type == HistoryEventType.STAKING and
                event.event_subtype == HistoryEventSubType.REWARD and
                event.asset == A_AAVE and
                event.location_label == to_address and
                event.amount == amount
                for event in context.decoded_events
            )
        ):
            claim_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.REWARD,
                asset=A_AAVE,
                amount=amount,
                location_label=to_address,
                notes=f'Claim {amount} AAVE from staking{suffix}',
                counterparty=CPT_AAVE,
                address=STK_AAVE_ADDR,
            )
            new_events.append(claim_event)

        maybe_reshuffle_events(
            ordered_events=(
                [claim_event, out_event, in_event]
                if claim_event is not None and claim_event not in context.decoded_events else
                [out_event, in_event]
            ),
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(events=new_events)

    def _decode_unstake(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            amount: FVal,
            context: DecoderContext,
    ) -> EvmDecodingOutput:
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == STKAAVE_IDENTIFIER and
                event.location_label == to_address and
                event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Unstake {amount} stkAAVE'
                if from_address != to_address:
                    event.notes += f' for {to_address}'
                event.counterparty = CPT_AAVE
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_AAVE and
                event.location_label == to_address and
                event.amount == amount
            ):
                event.counterparty = CPT_AAVE
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Receive {event.amount} AAVE after unstaking from Aave'

        return DEFAULT_EVM_DECODING_OUTPUT

    # DecoderInterface method
    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {STK_AAVE_ADDR: (self._decode_staking_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_AAVE,
            label=CPT_AAVE.capitalize(),
            image='aave.svg',
        ),)
