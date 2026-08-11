import logging
from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi
from eth_abi.exceptions import DecodingError

from rotkehlchen.assets.utils import asset_normalized_value, get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import (
    BRIDGE_TOPIC,
    CPT_SOCKET,
    GATEWAY_ADDRESS,
    PERFORM_ACTION_WITH_IN_SELECTOR,
    SWAP_AND_BRIDGE_SELECTOR,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import set_bridge_extra_data
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
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SocketBridgeDecoder(EvmDecoderInterface):
    """The gateway contract is deployed in all the chains with the same address"""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.eth = A_ETH.resolve_to_crypto_asset()

    @staticmethod
    def _decode_native_target_asset(transaction: EvmTransaction) -> ChecksumEvmAddress | None:
        """Return the native target hint from a directly decodable Socket route.

        Socket's route implementations are arbitrary calldata. This handles the known
        ``swapAndBridge`` route only and deliberately returns no hint for wrappers such as
        multicalls and Safe executions.
        """
        input_data = transaction.input_data
        if (
            len(input_data) < 8 or
            input_data[4:8] != SWAP_AND_BRIDGE_SELECTOR
        ):
            return None

        try:
            _, swap_data, _ = decode_abi(
                types=[
                    'uint32',
                    'bytes',
                    '(address,address,uint256,uint256,uint256,uint256,uint256,uint256,bytes32)',
                ],
                data=input_data[8:],
            )
            if not swap_data.startswith(PERFORM_ACTION_WITH_IN_SELECTOR):  # pylint: disable=no-member
                return None

            _, _, _, _, action_data = decode_abi(
                types=['address', 'address', 'uint256', 'bytes32', 'bytes'],
                data=swap_data[4:],
            )
        except (DecodingError, ValueError, IndexError):
            return None

        native_sentinel = bytes.fromhex(ETH_SPECIAL_ADDRESS[2:])
        if action_data.count(native_sentinel) != 1:  # pylint: disable=no-member
            return None

        return ZERO_ADDRESS

    def _decode_bridged_asset(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != BRIDGE_TOPIC:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount_raw = int.from_bytes(context.tx_log.data[0:32])
        token_address = bytes_to_address(context.tx_log.data[32:64])

        if token_address == ETH_SPECIAL_ADDRESS:
            bridged_asset: CryptoAsset = self.eth
        else:
            bridged_asset = get_or_create_evm_token(
                userdb=self.node_inquirer.database,
                evm_address=token_address,
                chain_id=self.node_inquirer.chain_id,
                evm_inquirer=self.node_inquirer,
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

        target_asset = self._decode_native_target_asset(transaction=context.transaction)
        for event in context.decoded_events:
            if (
                event.location_label == sender and
                event.address == GATEWAY_ADDRESS and
                event.event_type == HistoryEventType.SPEND
            ):
                direct_transfer = event.asset == bridged_asset and event.amount == amount
                swapped_transfer = event.event_subtype == HistoryEventSubType.NONE
                if not direct_transfer and not swapped_transfer:
                    continue

                # Socket can swap the user's source token before emitting the bridge event. In
                # that case the event token and amount describe the token sent by the gateway,
                # while the user's spend is the transfer to the gateway itself.
                if self.base.is_tracked(receiver):  # if receiver is not tracked we are spending it
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.BRIDGE
                    set_bridge_extra_data(  # the metadata field is an integrator id, not a transfer id, so there is no transfer_id to extract  # noqa: E501
                        event=event,
                        from_chain=self.node_inquirer.chain_id,
                        to_chain=to_chain_id_raw,
                        from_address=sender,
                        to_address=receiver,
                        to_asset=target_asset,
                    )

                event.counterparty = CPT_SOCKET
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} to {receiver} at {target_chain} using Socket'  # noqa: E501
                )
                break

        return DEFAULT_EVM_DECODING_OUTPUT

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
