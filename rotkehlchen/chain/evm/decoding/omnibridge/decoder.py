import abc
import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.utils import asset_normalized_value, get_or_create_evm_token
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.decoding.constants import GNOSIS_CPT_DETAILS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.evm_event import BRIDGE_EXTRA_DATA_KEY
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChainID, ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TOKENS_BRIDGING_INITIATED: Final = b'Y\xa9\xa8\x02{\x9c\x87\xb9a\xe2T\x89\x98!\xc9\xa2v\xb5\xef\xc3]\x1ft\t\xeaO)\x14p\xf1b\x9a'  # noqa: E501
TOKENS_BRIDGED: Final = b'\x9a\xfdG\x90~%\x02\x8c\xda\xca\x89\xd1\x93Q\x8c0+\xbb\x12\x86\x17\xd5\xa9\x92\xc5\xab\xd4X\x15Re\x93'  # noqa: E501
FEE_DISTRIBUTED: Final = b'\xd5`\xa5"\xf7|\xfbI$\xd6\xfeQ\xbe\x16\x15\xe5@\xa4\x8a\x891\xc4\x8f\xe04\x9c\x7fG\xeb\xab\xe7G'  # noqa: E501


class OmnibridgeCommonDecoder(EvmDecoderInterface, abc.ABC):

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
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

    def _decode_bridge_tokens(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes a bridging event for tokens. Either a deposit or a withdrawal."""
        if context.tx_log.topics[0] == TOKENS_BRIDGING_INITIATED:
            from_address = context.transaction.from_address
            to_address = from_address  # We have no to_address information
        elif context.tx_log.topics[0] == TOKENS_BRIDGED:
            to_address = bytes_to_address(context.tx_log.topics[2])
            from_address = to_address  # We have no from_address information
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

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
        fee_amount = ZERO
        if context.tx_log.topics[0] == TOKENS_BRIDGING_INITIATED:
            # For fee-charged tokens the mediator takes a fee before bridging, so the
            # TokensBridgingInitiated amount is lower than what the user transferred in
            for tx_log in context.all_logs:
                if (
                    tx_log.address == context.tx_log.address and
                    tx_log.topics[0] == FEE_DISTRIBUTED and
                    tx_log.topics[1] == context.tx_log.topics[1] and  # same token
                    tx_log.topics[2] == context.tx_log.topics[3]  # same AMB message id
                ):
                    fee_amount = asset_normalized_value(
                        amount=int.from_bytes(tx_log.data[0:32]),
                        asset=bridged_asset,
                    )
                    break

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
                event.amount == amount + fee_amount
            ):
                event.amount = amount  # deduct any bridge fee (split into its own event below)
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
                    transfer_id=f'0x{context.tx_log.topics[3].hex()}',  # the AMB message id
                )
                if event.extra_data is not None:
                    # the counterpart chain's address is not stated in the logs, so drop
                    # the fabricated one and keep only what this side's log actually states
                    event.extra_data[BRIDGE_EXTRA_DATA_KEY].pop(
                        'to_address' if context.tx_log.topics[0] == TOKENS_BRIDGING_INITIATED else 'from_address',  # noqa: E501
                    )
                if fee_amount > ZERO:
                    fee_event = self.base.make_event_next_index(
                        tx_ref=event.tx_ref,
                        timestamp=context.transaction.timestamp,
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.FEE,
                        asset=event.asset,
                        amount=fee_amount,
                        location_label=event.location_label,
                        notes=f'Spend {fee_amount} {bridged_asset.symbol} as a {GNOSIS_CPT_DETAILS.label} bridge fee',  # noqa: E501
                        counterparty=GNOSIS_CPT_DETAILS.identifier,
                        address=event.address,
                    )
                    context.decoded_events.append(fee_event)
                    maybe_reshuffle_events(
                        ordered_events=[event, fee_event],
                        events_list=context.decoded_events,
                    )
                break
        else:
            log.error(f'Could not find the transfer event for bridging to {to_address} in {context.transaction}')  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.bridge_address: (self._decode_bridge_tokens,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSIS_CPT_DETAILS,)
