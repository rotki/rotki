import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import (
    BRIDGE_TOPIC,
    CPT_SOCKET,
    GATEWAY_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SocketBridgeDecoder(DecoderInterface):
    """The gateway contract is deployed in all the chains with the same address"""

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_bridged_asset(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != BRIDGE_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        amount_raw = int.from_bytes(context.tx_log.data[0:32])
        token_address = bytes_to_address(context.tx_log.data[32:64])

        if token_address == ETH_SPECIAL_ADDRESS:
            bridged_asset: CryptoAsset = self.eth
        else:
            bridged_asset = get_or_create_evm_token(
                userdb=self.evm_inquirer.database,
                evm_address=token_address,
                chain_id=self.evm_inquirer.chain_id,
                evm_inquirer=self.evm_inquirer,
            )
        amount = asset_normalized_value(amount=amount_raw, asset=bridged_asset)
        sender = bytes_to_address(context.tx_log.data[128:160])
        receiver = bytes_to_address(context.tx_log.data[160:192])
        to_chain_id_raw = int.from_bytes(context.tx_log.data[64:96])

        try:
            to_chain_id = ChainID.deserialize_from_db(to_chain_id_raw)
            _, target_chain = to_chain_id.name_and_label()
        except DeserializationError:
            target_chain = str(to_chain_id_raw)
            log.error(f'Unknown to_chain in socket bridge: {to_chain_id_raw}')

        for event in context.decoded_events:
            if (
                event.location_label == sender and
                event.asset == bridged_asset and
                event.amount == amount and
                event.event_type == HistoryEventType.SPEND
            ):
                if self.base.is_tracked(receiver):  # if receiver is not tracked we are spending it  # noqa: E501
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.BRIDGE

                event.counterparty = CPT_SOCKET
                event.notes = (
                    f'Bridge {amount} {bridged_asset.symbol} to {receiver} at {target_chain} using Socket'  # noqa: E501
                )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GATEWAY_ADDRESS: (self._decode_bridged_asset,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_SOCKET,
                label='Socket',
                image='socket.png',
            ),
        )
