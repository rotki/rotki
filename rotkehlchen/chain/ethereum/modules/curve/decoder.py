import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.ethereum.modules.curve.constants import (
    AAVE_POOLS,
    CRV_ADDRESS,
    CURVE_DEPOSIT_CONTRACTS,
    CURVE_SWAP_ROUTER,
    GAUGE_BRIBE_V2,
    GAUGE_CONTROLLER,
)
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.curve.decoder import CurveCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.constants.assets import A_CRV, A_ETH
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveDecoder(CurveCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            native_currency=A_ETH,
            aave_pools=AAVE_POOLS,
            curve_deposit_contracts=CURVE_DEPOSIT_CONTRACTS,
            curve_swap_router=CURVE_SWAP_ROUTER,
            gauge_controller=GAUGE_CONTROLLER,
        )

    def _decode_gauge_bribe(self, context: DecoderContext) -> DecodingOutput:
        """Back in the day they had bribe directly in the gauge giving CRV. So this is """
        if (
                context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                hex_or_bytes_to_address(context.tx_log.topics[1]) == GAUGE_BRIBE_V2 and  # from
                self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
        ):
            suffix = '' if user_address == context.transaction.from_address else f' for {user_address}'  # noqa: E501
            action_item = ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=A_CRV,
                to_event_subtype=HistoryEventSubType.REWARD,
                to_notes=f'Claim {{amount}} CRV as veCRV voting bribe{suffix}',  # amount filled in by action item  # noqa: E501
                to_counterparty=CPT_CURVE,
            )
            return DecodingOutput(action_items=[action_item], matched_counterparty=CPT_CURVE)

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods
    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_CURVE: super(CurveDecoder, CurveDecoder).possible_products().get(CPT_CURVE, []) + [EvmProduct.BRIBE],  # noqa: E501
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            CRV_ADDRESS: (self._decode_gauge_bribe,),
        }
