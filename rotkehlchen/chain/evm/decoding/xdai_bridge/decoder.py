import abc
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.decoding.constants import GNOSIS_CPT_DETAILS
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class XdaiBridgeCommonDecoder(EvmDecoderInterface, abc.ABC):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            deposit_topics: tuple[bytes, ...],
            withdrawal_topic: bytes | None,  # withdrawal is currently unsupported on gnosis
            bridge_address: ChecksumEvmAddress,
            bridged_asset: 'Asset',
            source_chain: ChainID,
            target_chain: ChainID,
            peripheral_addresses: tuple[ChecksumEvmAddress, ...] | None = None,
    ) -> None:
        """Common decoder for the xDAI bridge.

        `bridge_address` - address of the bridge contract on this chain
        `bridged_asset` - the asset used on this chain's side of the bridge
        `source_chain` - the chain this instance of the decoder is on
        `target_chain` - the chain on the other side of the bridge
        `peripheral_addresses` - addresses of contracts used in connection with the bridge
           (used to convert assets before bridging for instance)
        """
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bridge_address = bridge_address
        self.bridged_asset = bridged_asset.resolve_to_crypto_asset()
        self.deposit_topics = deposit_topics
        self.withdrawal_topic = withdrawal_topic
        self.source_chain = source_chain
        self.target_chain = target_chain
        self.peripheral_addresses = peripheral_addresses or ()

    def _decode_bridged_asset(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes a bridging event for the `bridged_asset`, either a deposit or a withdrawal."""
        create_event = False
        if context.tx_log.topics[0] in self.deposit_topics:
            from_address = context.transaction.from_address
            to_address = self.bridge_address
        elif context.tx_log.topics[0] == self.withdrawal_topic:
            from_address = self.bridge_address
            to_address = bytes_to_address(context.tx_log.data[0:32])
            if self.source_chain == ChainID.GNOSIS and self.target_chain == ChainID.ETHEREUM:
                create_event = True

        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        amount = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[32:64]),
            asset=self.bridged_asset,
        )
        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,
            deposit_topics=self.deposit_topics,
            source_chain=self.source_chain,
            target_chain=self.target_chain,
            from_address=from_address,
            to_address=to_address,
        )

        if create_event:  # the bridge to gnosis from ethereum case
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=new_event_type,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=self.bridged_asset,
                amount=amount,
                location_label=to_address,
                notes='',
                counterparty=None,
                address=self.bridge_address,
            )
            bridge_match_transfer(
                event=event,
                from_address=to_address,  # we have no from_address information
                to_address=to_address,
                from_chain=from_chain,
                to_chain=to_chain,
                amount=event.amount,
                asset=self.bridged_asset,
                expected_event_type=HistoryEventType.RECEIVE,
                new_event_type=new_event_type,
                counterparty=GNOSIS_CPT_DETAILS,
            )
            return EvmDecodingOutput(events=[event])

        for event in context.decoded_events:
            if (
                event.event_type == expected_event_type and
                event.location_label == expected_location_label and
                (event.address == self.bridge_address or event.address in self.peripheral_addresses) and  # noqa: E501
                event.asset == self.bridged_asset and
                event.amount == amount
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=context.transaction.from_address,
                    to_address=bytes_to_address(context.tx_log.data[0:32]),
                    from_chain=from_chain,
                    to_chain=to_chain,
                    amount=event.amount,
                    asset=self.bridged_asset,
                    expected_event_type=expected_event_type,
                    new_event_type=new_event_type,
                    counterparty=GNOSIS_CPT_DETAILS,
                )
                break
        else:
            log.error(
                f'Could not find the transfer event for bridging to {to_address}'
                f' in {self.node_inquirer.chain_name} transaction {context.transaction.tx_hash.hex()}',  # noqa: E501
            )
        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.bridge_address: (self._decode_bridged_asset,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSIS_CPT_DETAILS,)
