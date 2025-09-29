from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.spark.constants import (
    SPARK_AIRDROP_DISTRIBUTOR,
    SPARK_STAKE_TOKEN,
)
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, DEPOSIT_TOPIC
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.decoding.spark.lend.decoder import SparklendCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

SPARK_CLAIM_SIGNATURE: Final = b'\xce;\xcbn!\x95\x96\xcf&\x00\x7f\xfd\xfa\xae\x89S\xbc?v\xe3\xf3l\ny\xb2>(\x02\r\xa3".'  # noqa: E501

SPARK_ASSET_ID: Final = 'eip155:1/erc20:0xc20059e0317DE91738d13af027DfC4a50781b066'


class SparklendDecoder(SparklendCommonDecoder, MerkleClaimDecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0xC13e21B648A5Ee794902342038FF3aDAB66BE987'),),
            native_gateways=(string_to_evm_address('0xBD7D6a9ad7865463DE44B05F04559f65e3B11704'),),
            treasury=string_to_evm_address('0xb137E7d16564c81ae2b0C8ee6B55De81dd46ECe5'),
            incentives=string_to_evm_address('0x4370D3b6C9588E02ce9D22e684387859c7Ff5b34'),
        )

    def _decode_spark_airdrop_claim(self, context: DecoderContext) -> DecodingOutput:
        """Decode Spark airdrop claims using the ClaimReward event"""
        if context.tx_log.topics[0] != SPARK_CLAIM_SIGNATURE:
            return DEFAULT_DECODING_OUTPUT

        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # SPK 18 decimals
        )
        user_address = bytes_to_address(context.tx_log.topics[2])

        # Find and modify the existing RECEIVE/NONE event to make it an airdrop event
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.asset.identifier == SPARK_ASSET_ID and
                event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.AIRDROP
                event.counterparty = CPT_SPARK
                event.notes = f'Claim {amount} SPK from Spark airdrop'
                event.address = context.tx_log.address
                event.extra_data = {AIRDROP_IDENTIFIER_KEY: 'spark'}
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_spark_staking(self, context: DecoderContext) -> DecodingOutput:
        """Decode Spark token staking into the staking contract"""
        if context.tx_log.topics[0] != DEPOSIT_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        user_address = bytes_to_address(context.tx_log.topics[1])
        raw_amount = int.from_bytes(context.tx_log.data[0:32])
        amount = token_normalized_value_decimals(
            token_amount=raw_amount,
            token_decimals=DEFAULT_TOKEN_DECIMALS,  # SPK 18 decimals
        )

        # Find and modify the existing SPEND/NONE event to make it a deposit for wrapped event
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == user_address and
                event.asset.identifier == SPARK_ASSET_ID and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = CPT_SPARK
                event.notes = f'Deposit {amount} SPK for staking'
                break

        # Use ActionItem to transform the stSPK receipt token event that comes later
        context.action_items.append(ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0xc6132FAF04627c8d05d6E759FAbB331Ef2D8F8fD'),
            amount=amount,
            location_label=user_address,
            to_event_type=HistoryEventType.RECEIVE,
            to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            to_notes=f'Receive {amount} stSPK for deposited SPK',
            to_counterparty=CPT_SPARK,
        ))

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        """Map contract addresses to their respective decoder methods"""
        return super().addresses_to_decoders() | {
            SPARK_AIRDROP_DISTRIBUTOR: (self._decode_spark_airdrop_claim,),
            SPARK_STAKE_TOKEN: (self._decode_spark_staking,),
        }
