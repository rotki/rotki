from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.evm.decoding.extrafi.constants import CPT_EXTRAFI
from rotkehlchen.chain.evm.decoding.extrafi.decoder import ExtrafiCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_OP
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

from .constants import EXTRAFI_COMMUNITY_FUND

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class ExtrafiDecoder(ExtrafiCommonDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            extra_token_identifier='eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8',
        )

    def _handle_op_rewards(self, context: DecoderContext) -> EvmDecodingOutput:
        """For a period of time extrafi gave/gives extra incentives for pool depositors by
        sending them directly to user addresses from their community fund"""
        if context.tx_log.topics[0] != b'fu<\xd25ei\xee\x08\x122\xe3\xbe\x89\t\xb9P\xe0\xa7l\x1f\x84`\xc3\xa5\xe3\xc2\xbe2\xb1\x1b\xed':  # SafeMultiSigTransaction # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        # If this transaction appears in your history you most probably received an Optimism
        # incentive reward, so create an action item to find it and mark it appropriately
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=A_OP,
            to_event_subtype=HistoryEventSubType.REWARD,
            to_notes='Receive {amount} OP as a reward incentive for participating in an Extrafi pool',  # noqa: E501
            to_counterparty=CPT_EXTRAFI,
        )
        return EvmDecodingOutput(action_items=[action_item])

    def addresses_to_decoders(self) -> dict['ChecksumEvmAddress', tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            EXTRAFI_COMMUNITY_FUND: (self._handle_op_rewards,),
        }
