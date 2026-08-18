import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import asset_normalized_value, get_or_create_evm_token
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.chain.evm.decoding.across.constants import DEPOSIT_TOPICS
from rotkehlchen.chain.evm.decoding.cctp.constants import CCTP_DOMAIN_MAPPING, DEPOSIT_FOR_BURN
from rotkehlchen.chain.evm.decoding.hop.constants import TRANSFER_SENT
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import (
    ACROSS_BRIDGE_NAME,
    BRIDGE_TOPIC,
    CCTP_BRIDGE_NAME,
    CPT_SOCKET,
    ETHEREUM_POLYGON_STATE_SYNCER,
    ETHEREUM_SCROLL_MESSENGER,
    GATEWAY_ADDRESS,
    GNOSIS_BRIDGE_NAMES,
    HOP_BRIDGE_NAME,
    OMNIBRIDGE_TOKENS_BRIDGING_INITIATED,
    POLYGON_BRIDGE_NAME,
    POLYGON_STATE_SYNCED,
    SCROLL_BRIDGE_NAME,
    XDAI_USER_REQUESTED_FOR_AFFIRMATION,
    XDAI_USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.superchain_bridge.l1.decoder import (
    ERC20_DEPOSIT_INITIATED,
    ETH_DEPOSIT_INITIATED,
)
from rotkehlchen.chain.evm.decoding.superchain_bridge.utils import get_messenger_transfer_id
from rotkehlchen.chain.evm.decoding.utils import set_bridge_extra_data
from rotkehlchen.chain.scroll.utils import get_scroll_messenger_transfer_id
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
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CCTP_CHAIN_TO_DOMAIN: Final = {
    chain_id.serialize(): domain for domain, chain_id in CCTP_DOMAIN_MAPPING.items()
}
OP_STACK_CHAIN_IDS: Final = {ChainID.OPTIMISM.serialize(), ChainID.BASE.serialize()}


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
    def _get_cctp_transfer_ids(
            all_logs: list[EvmTxReceiptLog],
            to_chain: int,
            receiver: ChecksumEvmAddress,
    ) -> set[str]:
        if (destination_domain := CCTP_CHAIN_TO_DOMAIN.get(to_chain)) is None:
            return set()

        return {
            str(int.from_bytes(tx_log.topics[1]))
            for tx_log in all_logs
            if (
                len(tx_log.topics) >= 4 and
                len(tx_log.data) >= 96 and
                tx_log.topics[0] == DEPOSIT_FOR_BURN and
                bytes_to_address(tx_log.data[32:64]) == receiver and
                int.from_bytes(tx_log.data[64:96]) == destination_domain
            )
        }

    @staticmethod
    def _get_gnosis_transfer_ids(
            all_logs: list[EvmTxReceiptLog],
            source_tx_hash: str,
    ) -> set[str]:
        transfer_ids = {
            f'0x{tx_log.topics[3].hex()}'
            for tx_log in all_logs
            if (
                len(tx_log.topics) >= 4 and
                tx_log.topics[0] == OMNIBRIDGE_TOKENS_BRIDGING_INITIATED
            )
        }
        if any(
            len(tx_log.topics) != 0 and
            tx_log.topics[0] in {
                XDAI_USER_REQUESTED_FOR_AFFIRMATION,
                XDAI_USER_REQUESTED_FOR_AFFIRMATION_WITH_NONCE,
            }
            for tx_log in all_logs
        ):
            transfer_ids.add(source_tx_hash)

        return transfer_ids

    @staticmethod
    def _is_matching_op_stack_deposit(
            tx_log: EvmTxReceiptLog,
            receiver: ChecksumEvmAddress,
    ) -> bool:
        if len(tx_log.topics) == 0:
            return False
        if tx_log.topics[0] == ETH_DEPOSIT_INITIATED:
            return len(tx_log.topics) >= 3 and bytes_to_address(tx_log.topics[2]) == receiver
        if tx_log.topics[0] == ERC20_DEPOSIT_INITIATED:
            return (
                len(tx_log.topics) >= 4 and
                len(tx_log.data) >= 32 and
                bytes_to_address(tx_log.data[:32]) == receiver
            )
        return False

    @classmethod
    def _get_op_stack_transfer_ids(
            cls,
            all_logs: list[EvmTxReceiptLog],
            to_chain: int,
            receiver: ChecksumEvmAddress,
    ) -> set[str]:
        if (
            to_chain not in OP_STACK_CHAIN_IDS or
            not any(cls._is_matching_op_stack_deposit(tx_log, receiver) for tx_log in all_logs) or
            (transfer_id := get_messenger_transfer_id(all_logs)) is None
        ):
            return set()
        return {transfer_id}

    @staticmethod
    def _get_underlying_transfer_id(
            all_logs: list[EvmTxReceiptLog],
            source_tx_hash: str,
            bridge_name: bytes,
            to_chain: int,
            sender: ChecksumEvmAddress,
            receiver: ChecksumEvmAddress,
    ) -> str | None:
        """Return the protocol transfer id emitted by the underlying Socket route.

        Socket is an aggregator, so its own bridge event has no transfer id. The underlying
        bridge protocol emits the exact id later used by its destination event. Protocol,
        chain and participant checks prevent unrelated logs in the transaction from being used.
        """
        if bridge_name == HOP_BRIDGE_NAME:
            transfer_ids = {
                '0x' + tx_log.topics[1].hex()
                for tx_log in all_logs
                if (
                    len(tx_log.topics) >= 4 and
                    tx_log.topics[0] == TRANSFER_SENT and
                    int.from_bytes(tx_log.topics[2]) == to_chain and
                    bytes_to_address(tx_log.topics[3]) == receiver
                )
            }
        elif bridge_name == ACROSS_BRIDGE_NAME:
            transfer_ids = {
                str(int.from_bytes(tx_log.topics[2]))
                for tx_log in all_logs
                if (
                    len(tx_log.topics) >= 4 and
                    len(tx_log.data) >= 256 and
                    tx_log.topics[0] in DEPOSIT_TOPICS and
                    int.from_bytes(tx_log.topics[1]) == to_chain and
                    bytes_to_address(tx_log.topics[3]) == sender and
                    bytes_to_address(tx_log.data[224:256]) == receiver
                )
            }
        elif bridge_name == CCTP_BRIDGE_NAME:
            transfer_ids = SocketBridgeDecoder._get_cctp_transfer_ids(
                all_logs=all_logs,
                to_chain=to_chain,
                receiver=receiver,
            )
        elif bridge_name in GNOSIS_BRIDGE_NAMES and to_chain == ChainID.GNOSIS.serialize():
            transfer_ids = SocketBridgeDecoder._get_gnosis_transfer_ids(
                all_logs=all_logs,
                source_tx_hash=source_tx_hash,
            )
        elif bridge_name == POLYGON_BRIDGE_NAME and to_chain == ChainID.POLYGON_POS.serialize():
            transfer_ids = {
                str(int.from_bytes(tx_log.topics[1]))
                for tx_log in all_logs
                if (
                    len(tx_log.topics) >= 2 and
                    tx_log.address == ETHEREUM_POLYGON_STATE_SYNCER and
                    tx_log.topics[0] == POLYGON_STATE_SYNCED
                )
            }
        elif bridge_name == SCROLL_BRIDGE_NAME and to_chain == ChainID.SCROLL.serialize():
            transfer_ids = set()
            if (transfer_id := get_scroll_messenger_transfer_id(
                all_logs=all_logs,
                messenger=ETHEREUM_SCROLL_MESSENGER,
            )) is not None:
                transfer_ids.add(transfer_id)
        else:
            transfer_ids = SocketBridgeDecoder._get_op_stack_transfer_ids(
                all_logs=all_logs,
                to_chain=to_chain,
                receiver=receiver,
            )

        if len(transfer_ids) != 1:
            return None
        return transfer_ids.pop()

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
        bridge_name = context.tx_log.data[96:128]

        try:
            to_chain_id = ChainID.deserialize_from_db(to_chain_id_raw)
            _, target_chain = to_chain_id.name_and_label()
        except DeserializationError:
            target_chain = str(to_chain_id_raw)
            log.error(f'Unknown to_chain in socket bridge: {to_chain_id_raw}')

        transfer_id = self._get_underlying_transfer_id(
            all_logs=context.all_logs,
            source_tx_hash=context.transaction.tx_hash.hex(),
            bridge_name=bridge_name,
            to_chain=to_chain_id_raw,
            sender=sender,
            receiver=receiver,
        )
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
                    set_bridge_extra_data(
                        event=event,
                        from_chain=self.node_inquirer.chain_id,
                        to_chain=to_chain_id_raw,
                        from_address=sender,
                        to_address=receiver,
                        transfer_id=transfer_id,
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
