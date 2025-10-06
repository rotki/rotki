from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.odos.v2.constants import CPT_ODOS_V2
from rotkehlchen.chain.evm.decoding.odos.v2.decoder import Odosv2DecoderBase
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    ODOS_AIRDROP_DISTRIBUTOR,
    ODOS_ASSET_ID,
    ODOS_V2_ROUTER,
    REWARD_CLAIMED_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class Odosv2Decoder(Odosv2DecoderBase):
    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=ODOS_V2_ROUTER,
        )

    def decode_claim(self, context: 'DecoderContext') -> 'EvmDecodingOutput':
        if (
            context.tx_log.topics[0] != REWARD_CLAIMED_TOPIC or
            context.tx_log.address != ODOS_AIRDROP_DISTRIBUTOR
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        if self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2])) is False:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[0:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                event.address == ODOS_AIRDROP_DISTRIBUTOR and
                event.asset.identifier == ODOS_ASSET_ID and
                event.location_label == recipient and
                event.amount == amount and
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_ODOS_V2
                event.notes = f'Claim {amount} ODOS from Odos airdrop'
                event.extra_data = {AIRDROP_IDENTIFIER_KEY: 'odos'}

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            string_to_evm_address('0x4C8f8055D88705f52c9994969DDe61AB574895a3'): (self.decode_claim,),  # noqa: E501
        }
