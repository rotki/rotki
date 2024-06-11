from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.curve.constants import (
    CPT_CURVE,
    CURVE_SWAP_ROUTER_NG,
    GAUGE_VOTE,
)
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
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import (
    AAVE_POOLS,
    CRV_ADDRESS,
    CURVE_DEPOSIT_CONTRACTS,
    CURVE_SWAP_ROUTER,
    DEPOSIT_AND_STAKE_ZAP,
    GAUGE_BRIBE_V2,
    GAUGE_CONTROLLER,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


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
            curve_deposit_contracts=CURVE_DEPOSIT_CONTRACTS | {DEPOSIT_AND_STAKE_ZAP},
            curve_swap_routers={CURVE_SWAP_ROUTER, CURVE_SWAP_ROUTER_NG},
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

    def _decode_curve_gauge_votes(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != GAUGE_VOTE:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := hex_or_bytes_to_address(context.tx_log.data[32:64])):  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        user_note = '' if user_address == context.transaction.from_address else f' from {user_address}'  # noqa: E501
        gauge_address = hex_or_bytes_to_address(context.tx_log.data[64:96])
        vote_weight = hex_or_bytes_to_int(context.tx_log.data[96:128])
        if vote_weight == 0:
            verb = 'Reset vote'
            weight_note = ''
        else:
            verb = 'Vote'
            weight_note = f' with {vote_weight / 100}% voting power'
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=self.native_currency,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'{verb}{user_note} for {gauge_address} curve gauge{weight_note}',
            address=gauge_address,
            counterparty=CPT_CURVE,
            product=EvmProduct.GAUGE,
        )
        return DecodingOutput(event=event, refresh_balances=False)

    # -- DecoderInterface methods
    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_CURVE: super(CurveDecoder, CurveDecoder).possible_products().get(CPT_CURVE, []) + [EvmProduct.BRIBE],  # noqa: E501
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return super().addresses_to_decoders() | {
            GAUGE_CONTROLLER: (self._decode_curve_gauge_votes,),
            CRV_ADDRESS: (self._decode_gauge_bribe,),
        }
