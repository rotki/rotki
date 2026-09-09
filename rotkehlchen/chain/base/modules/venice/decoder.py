from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.base.modules.venice.constants import (
    CPT_VENICE,
    DIEM_BURNED,
    DIEM_MINTED,
    DIEM_TOKEN_ID,
    SVVV_TOKEN_ID,
    VENICE_AIRDROP_CONTRACT,
    VENICE_CLAIMED,
    VENICE_STAKING_CONTRACT,
    VENICE_STAKING_REWARD_CLAIMED,
    VVV_TOKEN_ID,
)
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import STAKED
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext
    from rotkehlchen.types import ChecksumEvmAddress


class VeniceDecoder(MerkleClaimDecoderInterface):

    def _decode_airdrop_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != VENICE_CLAIMED:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(
                claiming_address := bytes_to_address(context.tx_log.topics[1]),
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        claimed_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token_decimals=18,
        )
        return self._maybe_enrich_claim_transfer(
            context=context,
            counterparty=CPT_VENICE,
            token_id=VVV_TOKEN_ID,
            notes_suffix='VVV from Venice airdrop',
            claiming_address=claiming_address,
            claimed_amount=claimed_amount,
            airdrop_identifiers='venice',
        )

    def _decode_stake(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DIEM_MINTED:
            return self._decode_diem_mint(context)
        if context.tx_log.topics[0] == DIEM_BURNED:
            return self._decode_diem_burn(context)

        if (
            context.tx_log.topics[0] not in (STAKED, VENICE_STAKING_REWARD_CLAIMED) or
            not self.base.is_tracked(
                user_address := bytes_to_address(context.tx_log.topics[1]),
            )
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=18,
        )
        if context.tx_log.topics[0] == VENICE_STAKING_REWARD_CLAIMED:
            for event in context.decoded_events:
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.location_label == user_address and
                    event.address == VENICE_STAKING_CONTRACT and
                    event.asset.identifier == VVV_TOKEN_ID and
                    event.amount == amount
                ):
                    event.event_type = HistoryEventType.STAKING
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.counterparty = CPT_VENICE
                    event.notes = f'Claim {amount} VVV staking reward from Venice'
                    break

            return DEFAULT_EVM_DECODING_OUTPUT
        staking_event = receive_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.location_label == user_address and
                event.address == VENICE_STAKING_CONTRACT and
                event.asset.identifier == VVV_TOKEN_ID and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_VENICE
                event.notes = f'Stake {amount} VVV'
                staking_event = event
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == user_address and
                event.asset.identifier == SVVV_TOKEN_ID and
                event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = CPT_VENICE
                event.notes = f'Receive {amount} sVVV after staking in Venice'
                receive_event = event

        if staking_event is not None and receive_event is not None:
            maybe_reshuffle_events(
                ordered_events=[staking_event, receive_event],
                events_list=context.decoded_events,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_diem_mint(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(user_address := context.transaction.from_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        locked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=18,
        )
        minted_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=18,
        )
        lock_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(SVVV_TOKEN_ID),
            amount=locked_amount,
            location_label=user_address,
            notes=f'Deposit {locked_amount} sVVV as collateral to mint DIEM',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        )
        mint_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == user_address and
                event.address == ZERO_ADDRESS and
                event.asset.identifier == DIEM_TOKEN_ID and
                event.amount == minted_amount
            ):
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_VENICE
                event.notes = f'Mint {minted_amount} DIEM by locking {locked_amount} sVVV'
                mint_event = event
                break

        maybe_reshuffle_events(
            ordered_events=[lock_event, mint_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(events=[lock_event])

    def _decode_diem_burn(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(user_address := context.transaction.from_address):
            return DEFAULT_EVM_DECODING_OUTPUT

        unlocked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=18,
        )
        burned_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=18,
        )
        unlock_event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset(SVVV_TOKEN_ID),
            amount=unlocked_amount,
            location_label=user_address,
            notes=f'Withdraw {unlocked_amount} sVVV collateral by burning DIEM',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        )
        burn_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.location_label == user_address and
                event.address == ZERO_ADDRESS and
                event.asset.identifier == DIEM_TOKEN_ID and
                event.amount == burned_amount
            ):
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_VENICE
                event.notes = f'Burn {burned_amount} DIEM to unlock {unlocked_amount} sVVV'
                burn_event = event
                break

        maybe_reshuffle_events(
            ordered_events=[burn_event, unlock_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(events=[unlock_event])

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            VENICE_AIRDROP_CONTRACT: (self._decode_airdrop_claim,),
            VENICE_STAKING_CONTRACT: (self._decode_stake,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_VENICE,
            label='Venice',
            image='venice.svg',
        ),)
