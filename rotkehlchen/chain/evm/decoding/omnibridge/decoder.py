import abc
import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.decoding.constants import GNOSIS_CPT_DETAILS
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOKENS_BRIDGING_INITIATED: Final = b'Y\xa9\xa8\x02{\x9c\x87\xb9a\xe2T\x89\x98!\xc9\xa2v\xb5\xef\xc3]\x1ft\t\xeaO)\x14p\xf1b\x9a'  # noqa: E501
TOKENS_BRIDGED: Final = b'\x9a\xfdG\x90~%\x02\x8c\xda\xca\x89\xd1\x93Q\x8c0+\xbb\x12\x86\x17\xd5\xa9\x92\xc5\xab\xd4X\x15Re\x93'  # noqa: E501


class OmnibridgeCommonDecoder(EvmDecoderInterface, abc.ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            bridge_address: ChecksumEvmAddress,
            source_chain: ChainID,
            target_chain: ChainID,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bridge_address = bridge_address
        self.source_chain = source_chain
        self.target_chain = target_chain

    def _decode_bridge_tokens(self, context: DecoderContext) -> DecodingOutput:
        """Decodes a bridging event for tokens. Either a deposit or a withdrawal."""
        if context.tx_log.topics[0] == TOKENS_BRIDGING_INITIATED:
            from_address = context.transaction.from_address
            to_address = from_address  # We have no to_address information
        elif context.tx_log.topics[0] == TOKENS_BRIDGED:
            to_address = bytes_to_address(context.tx_log.topics[2])
            from_address = to_address  # We have no from_address information
        else:
            return DEFAULT_DECODING_OUTPUT

        bridged_asset = get_or_create_evm_token(
            userdb=self.node_inquirer.database,
            evm_address=bytes_to_address(context.tx_log.topics[1]),
            chain_id=self.node_inquirer.chain_id,
            evm_inquirer=self.node_inquirer,
        )
        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[0:32]),
            asset=bridged_asset,
        )
        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,
            deposit_topics=(TOKENS_BRIDGING_INITIATED,),
            source_chain=self.source_chain,
            target_chain=self.target_chain,
            from_address=from_address,
            to_address=to_address,
        )

        for event in context.decoded_events:
            if bridged_asset == A_WETH and event.asset == A_ETH and event.amount == amount:
                if event.event_type == HistoryEventType.RECEIVE:
                    # Use transaction.from_address in ETH withdrawals since tx_log.topics[2] has other data  # noqa: E501
                    expected_location_label = context.transaction.from_address
                    from_address = expected_location_label
                    to_address = expected_location_label
                expected_address = bytes_to_address(context.tx_log.topics[2])
                expected_asset = A_ETH
            else:
                expected_address = self.bridge_address
                expected_asset = bridged_asset

            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                event.address in (expected_address, ZERO_ADDRESS) and
                event.asset == expected_asset and
                event.amount == amount
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=from_address,
                    to_address=to_address,
                    from_chain=from_chain,
                    to_chain=to_chain,
                    amount=event.amount,
                    asset=bridged_asset,
                    expected_event_type=expected_event_type,
                    new_event_type=new_event_type,
                    counterparty=GNOSIS_CPT_DETAILS,
                )
                break
        else:
            log.error(f'Could not find the transfer event for bridging to {to_address} in {context.transaction}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.bridge_address: (self._decode_bridge_tokens,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSIS_CPT_DETAILS,)
