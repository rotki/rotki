import logging
from typing import Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.clique.decoder import CliqueAirdropDecoderInterface
from rotkehlchen.chain.evm.decoding.constants import STAKED
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_OMNI, OMNI_AIDROP_CONTRACT, OMNI_STAKING_CONTRACT, OMNI_TOKEN_ID

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OmniDecoder(CliqueAirdropDecoderInterface):

    def _decode_omni_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        transfer_found = False
        if not (decode_result := self._decode_claim(context)):
            return DEFAULT_EVM_DECODING_OUTPUT

        claiming_address, claimed_amount = decode_result
        notes = f'Claim {claimed_amount} OMNI from the Omni genesis airdrop'
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.location_label == claiming_address and
                event.asset.identifier == OMNI_TOKEN_ID and
                event.amount == claimed_amount
            ):
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_OMNI
                event.notes = notes
                event.extra_data = {AIRDROP_IDENTIFIER_KEY: 'omni'}
                transfer_found = True
            elif (
                event.event_type == HistoryEventType.SPEND and
                event.address == OMNI_AIDROP_CONTRACT and
                event.asset == A_ETH
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_OMNI
                event.notes = f'Spend {event.amount} ETH as a fee to claim the Omni genesis airdrop'  # noqa: E501

        if not transfer_found:  # it's claim and stake, so transfer is direct to stake
            claim_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                asset=Asset(OMNI_TOKEN_ID),
                amount=FVal(claimed_amount),
                location_label=claiming_address,
                notes=notes,
                counterparty=CPT_OMNI,
                address=OMNI_AIDROP_CONTRACT,
                extra_data={AIRDROP_IDENTIFIER_KEY: 'omni'},
            )
            for event in context.decoded_events:  # find the stake event and assure comes after
                if (
                        event.event_type == HistoryEventType.STAKING and
                        event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and
                        event.location_label == claiming_address and
                        event.asset.identifier == OMNI_TOKEN_ID and
                        event.amount == claimed_amount and
                        event.address == OMNI_STAKING_CONTRACT
                ):
                    maybe_reshuffle_events(
                        ordered_events=[claim_event, event],
                        events_list=context.decoded_events + [claim_event],
                    )
                    break
            else:
                log.error(f'Could not find stake event for an OMNI stake and claim action {context.transaction.tx_hash.hex()}')  # noqa: E501

            return EvmDecodingOutput(events=[claim_event])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_omni_stake(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != STAKED:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        staked_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data),
            token_decimals=18,  # omni has 18 decimals
        )
        transfer_found = False
        notes = f'Stake {staked_amount} OMNI'
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.location_label == user_address and
                event.address == OMNI_STAKING_CONTRACT and
                event.asset.identifier == OMNI_TOKEN_ID and
                event.amount == staked_amount
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_OMNI
                event.notes = notes
                transfer_found = True

        if not transfer_found:  # it's claim and stake so transfer is direct from airdrop contract
            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=Asset(OMNI_TOKEN_ID),
                amount=FVal(staked_amount),
                location_label=user_address,
                notes=notes,
                counterparty=CPT_OMNI,
                address=OMNI_STAKING_CONTRACT,
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            OMNI_AIDROP_CONTRACT: (self._decode_omni_claim,),
            OMNI_STAKING_CONTRACT: (self._decode_omni_stake,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_OMNI, label='Omni', image='omni.svg'),)
