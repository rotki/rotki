from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.types import ChainID, ChecksumEvmAddress, DecoderEventMappingType, Timestamp
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int, timestamp_to_date

from .constants import CPT_STAKEDAO, STAKEDAO_CLAIMER1, STAKEDAO_CLAIMER2

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


CLAIMED = b'o\x9c\x98&\xbeYv\xf3\xf8*4\x90\xc5*\x832\x8c\xe2\xec{\xe9\xe6-\xcb9\xc2m\xa5\x14\x8d|v'


class StakedaoDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _decode_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED:
            return DEFAULT_DECODING_OUTPUT

        # we are not checking user address in the logs as user is not always
        # the recipient according to the contract
        reward_token_address = hex_or_bytes_to_address(context.tx_log.data[0:32])
        amount = hex_or_bytes_to_int(context.tx_log.data[32:64])
        period = Timestamp(hex_or_bytes_to_int(context.tx_log.data[96:128]))
        claimed_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=reward_token_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=self.evm_inquirer,
        )
        normalized_amount = token_normalized_value(amount, claimed_token)

        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == claimed_token and event.balance.amount == normalized_amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_STAKEDAO
                event.notes = f'Claimed {normalized_amount} {claimed_token.symbol} from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}'  # noqa: E501
                break

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_STAKEDAO: {
            HistoryEventType.RECEIVE: {
                HistoryEventSubType.REWARD: EventCategory.CLAIM_REWARD,
            },
        }}

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            STAKEDAO_CLAIMER1: (self._decode_events,),
            STAKEDAO_CLAIMER2: (self._decode_events,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_STAKEDAO,
            label='Stakedao',
            image='stakedao.png',
        )]
