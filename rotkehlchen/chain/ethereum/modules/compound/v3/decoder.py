import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import COMPOUND_REWARDS_ADDRESS, CPT_COMPOUND_V3

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

REWARD_CLAIMED = b'$"\xca\xc5\xe2<F\xc8\x90\xfd\xcfB\xd0\xc6GW@\x9d\xf6\x83!t\xdfc\x937U\x8f\t\xd9\x9ch'  # noqa: E501


class Compoundv3Decoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def decode_reward_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode a compound v3 reward claiming"""
        if context.tx_log.topics[0] != REWARD_CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        recipient = hex_or_bytes_to_address(context.tx_log.topics[2])
        if not self.base.is_tracked(recipient):
            return DEFAULT_DECODING_OUTPUT

        reward_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=hex_or_bytes_to_address(context.tx_log.topics[3]),
            chain_id=self.base.evm_inquirer.chain_id,
            token_kind=EvmTokenKind.ERC20,
            evm_inquirer=self.base.evm_inquirer,
        )
        amount_raw = hex_or_bytes_to_int(context.tx_log.data)
        amount = asset_normalized_value(amount_raw, reward_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.location_label == recipient and event.asset == reward_token and event.address == COMPOUND_REWARDS_ADDRESS and event.balance.amount == amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_COMPOUND_V3
                event.notes = f'Collect {event.balance.amount} {reward_token.symbol} from compound'
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {COMPOUND_REWARDS_ADDRESS: (self.decode_reward_claim,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_COMPOUND_V3,
            label='Compound',
            image='compound.svg',
        ),)
