from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.assets.asset import AssetWithSymbol, EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import BASE_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

BRIDGE_ADDRESS = string_to_evm_address('0x49048044D57e1C92A77f79988d21Fa8fAF74E97e')
TOKEN_PORTAL = string_to_evm_address('0x3154Cf16ccdb4C6d922629664174b904d80F2C35')
TRANSACTION_DEPOSITED = b'\xb3\x815h\xd9\x99\x1f\xc9Q\x96\x1f\xcbLxH\x93WB@\xa2\x89%`M\t\xfcW|U\xbb|2'  # noqa: E501
WITHDRAWAL_FINALIZED = b"\xdb\\vR\x85z\xa1c\xda\xad\xd6p\xe1\x16b\x8f\xb4.\x86\x9d\x8a\xc4%\x1e\xf8\x97\x1d\x9eW'\xdf\x1b"  # noqa: E501
BRIDGE_TOKEN = b'\x7f\xf1&\xdb\x80$BK\xbf\xd9\x82n\x8a\xb8/\xf5\x916(\x9e\xa4@\xb0K9\xa0\xdf\x1b\x03\xb9\xca\xbf'  # noqa: E501
WITHDRAWAL_TOKEN = b'\xd5\x9ce\xb3TE"X5\xc8?P\xb6\xed\xe0j{\xe0G\xd2.5ps\xe2P\xd9\xafSu\x18\xcd'


class BaseBridgeDecoder(DecoderInterface):

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
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _find_event(
            self,
            context: DecoderContext,
            contract_address: ChecksumEvmAddress,
            deposit_event: bytes,
            asset: AssetWithSymbol,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            amount: Optional[FVal] = None,
    ) -> None:
        """Given the filters for the events update the information of the bridging events"""
        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,
            deposit_topics=(deposit_event,),
            source_chain=ChainID.ETHEREUM,
            target_chain=ChainID.BASE,
            from_address=from_address,
            to_address=to_address,
        )

        # Find the corresponding transfer event and update it
        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address == contract_address and
                event.asset == asset and
                (amount is None or event.balance.amount == amount)
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=from_address,
                    to_address=to_address,
                    from_chain=from_chain,
                    to_chain=to_chain,
                    amount=event.balance.amount,
                    asset=asset,
                    expected_event_type=expected_event_type,
                    new_event_type=new_event_type,
                    counterparty=BASE_CPT_DETAILS,
                )

    def _decode_bridge_eth(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging event for ETH. Either a deposit or a withdrawal."""
        if context.tx_log.topics[0] not in {TRANSACTION_DEPOSITED, WITHDRAWAL_FINALIZED}:
            # Make sure that we are decoding a supported event.
            return DEFAULT_DECODING_OUTPUT

        # Read information from event's topics & data
        if context.tx_log.topics[0] == TRANSACTION_DEPOSITED:
            from_address = hex_or_bytes_to_address(context.tx_log.topics[1])
            to_address = hex_or_bytes_to_address(context.tx_log.topics[2])
        else:
            from_address = context.transaction.from_address
            to_address = context.transaction.from_address

        self._find_event(
            context=context,
            contract_address=BRIDGE_ADDRESS,
            deposit_event=TRANSACTION_DEPOSITED,
            asset=self.eth,
            from_address=from_address,
            to_address=to_address,
        )
        return DEFAULT_DECODING_OUTPUT

    def _decode_bridge_tokens(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging event for tokens. Either a deposit or a withdrawal."""
        if context.tx_log.topics[0] not in {BRIDGE_TOKEN, WITHDRAWAL_TOKEN}:
            # Make sure that we are decoding a supported event.
            return DEFAULT_DECODING_OUTPUT

        # Read information from event's topics & data
        if context.tx_log.topics[0] == BRIDGE_TOKEN:
            from_address = hex_or_bytes_to_address(context.tx_log.topics[3])
            to_address = hex_or_bytes_to_address(context.tx_log.data[0:32])
        else:
            from_address = hex_or_bytes_to_address(context.tx_log.data[0:32])
            to_address = hex_or_bytes_to_address(context.tx_log.topics[3])

        raw_amount = hex_or_bytes_to_int(context.tx_log.data[32:64])
        asset = EvmToken(strethaddress_to_identifier(hex_or_bytes_to_address(context.tx_log.topics[1])))  # noqa: E501
        amount = asset_normalized_value(amount=raw_amount, asset=asset)

        self._find_event(
            context=context,
            contract_address=TOKEN_PORTAL,
            deposit_event=BRIDGE_TOKEN,
            asset=asset,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
        )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            BRIDGE_ADDRESS: (self._decode_bridge_eth,),
            TOKEN_PORTAL: (self._decode_bridge_tokens,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [BASE_CPT_DETAILS]
