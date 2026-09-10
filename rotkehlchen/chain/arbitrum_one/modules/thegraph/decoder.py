import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.modules.arbitrum_one_bridge.decoder import L2_TO_L1_TX
from rotkehlchen.chain.arbitrum_one.modules.thegraph.constants import (
    CONTRACT_STAKING,
    L2_GRAPH_TOKEN_LOCK_TRANSFER_TOOL,
    LOCKED_FUNDS_SENT_TO_L1,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.decoding.thegraph.decoder import ThegraphCommonDecoder
from rotkehlchen.chain.evm.decoding.utils import make_bridge_extra_data
from rotkehlchen.constants.assets import A_GRT_ARB
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ThegraphDecoder(ThegraphCommonDecoder):

    def __init__(
            self,
            arbitrum_one_inquirer: ArbitrumOneInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=arbitrum_one_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_asset=A_GRT_ARB,
            staking_contract=CONTRACT_STAKING,
        )

    def _decode_locked_funds_sent_to_l1(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode GRT being sent from an L2 vesting contract back to its L1 counterpart
        through the L2GraphTokenLockTransferTool (withdrawToL1Locked). The transfer tool pulls
        the GRT from the vesting contract and bridges it with the arbitrum gateway to the
        L1 vesting contract, where it has to be claimed from the outbox after 7 days."""
        if context.tx_log.topics[0] != LOCKED_FUNDS_SENT_TO_L1:
            return DEFAULT_EVM_DECODING_OUTPUT

        l1_wallet = bytes_to_address(context.tx_log.topics[1])
        if (resolved := self._resolve_delegator(l2_wallet := bytes_to_address(context.tx_log.topics[2]))) is None:  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        user_address, vesting_contract = resolved
        amount = token_normalized_value(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token=self.token,
        )
        if vesting_contract is not None:  # only the beneficiary is tracked. No transfer to edit
            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=self.token,
                amount=ZERO,
                location_label=user_address,
                notes=f'Bridge {amount} GRT from vesting contract {vesting_contract} on Arbitrum One to vesting contract {l1_wallet} on Ethereum',  # noqa: E501
                counterparty=CPT_THEGRAPH,
                address=context.tx_log.address,
            )])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == l2_wallet and
                event.address == context.tx_log.address and
                event.asset == self.token and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ARBITRUM_ONE
                event.notes = f'Bridge {amount} GRT from Arbitrum One to Ethereum vesting contract {l1_wallet} via Arbitrum One bridge'  # noqa: E501
                event.extra_data = make_bridge_extra_data(
                    from_chain=ChainID.ARBITRUM_ONE,
                    to_chain=ChainID.ETHEREUM,
                    from_address=l2_wallet,
                    to_address=l1_wallet,
                    transfer_id=next(  # position of the L2 to L1 message, matching the L1 outbox execution  # noqa: E501
                        (str(int.from_bytes(tx_log.topics[3])) for tx_log in context.all_logs if tx_log.topics[0] == L2_TO_L1_TX),  # noqa: E501
                        None,
                    ),
                )
                break
        else:
            log.error(
                'Could not find the GRT transfer of the vesting contract to the graph transfer tool',  # noqa: E501
                vesting_contract=l2_wallet,
                tx_hash=context.transaction.tx_hash,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            L2_GRAPH_TOKEN_LOCK_TRANSFER_TOOL: (self._decode_locked_funds_sent_to_l1,),
        }
