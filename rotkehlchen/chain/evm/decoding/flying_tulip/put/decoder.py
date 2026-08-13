from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.constants import UNSTAKE_TOPIC
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import FLYING_TULIP_LABEL
from rotkehlchen.chain.evm.decoding.flying_tulip.decoder import FlyingTulipCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    DIVESTED_TOPIC,
    FLYING_TULIP_PUT_DEPLOYMENTS,
    INVESTED_TOPIC,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator


class FlyingTulipPutCommonDecoder(FlyingTulipCommonDecoder):
    """Decode ftPUT activity (Flying Tulip's FT put positions).

    Investing allocates FT inside a put position NFT in exchange for
    collateral. Divesting returns collateral at the strike price, while
    withdrawing takes the allocated FT out of the position instead.
    """

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
        self.deployment = FLYING_TULIP_PUT_DEPLOYMENTS[evm_inquirer.chain_id]

    def _decode_put_manager(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == INVESTED_TOPIC:
            investor = bytes_to_address(context.tx_log.data[0:32])
            recipient = bytes_to_address(context.tx_log.data[32:64])  # position recipient
            if not self.base.any_tracked([investor, recipient]):
                return DEFAULT_EVM_DECODING_OUTPUT

            position_id = int.from_bytes(context.tx_log.data[64:96])
            token = self.base.get_or_create_evm_token(
                address=bytes_to_address(context.tx_log.data[160:192]),
            )
            amount = token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[192:224]),
                token=token,
            )
            # An investment is either funded straight into the manager, or the
            # user funds an investing proxy which then appears as the investor,
            # so the eligible transfer counterparties are exactly those two.
            self._transform_matching_event(
                context=context,
                from_event_type=HistoryEventType.SPEND,
                token=token,
                amount=amount,
                allowed_labels=(investor, recipient),
                allowed_addresses=(self.deployment.put_manager, investor),
                to_event_type=HistoryEventType.DEPOSIT,
                to_event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                notes=f'Invest {amount} {token.symbol} in {FLYING_TULIP_LABEL} put position #{position_id}',  # noqa: E501
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == DIVESTED_TOPIC:
            if not self.base.is_tracked(
                divestor := bytes_to_address(context.tx_log.data[0:32]),
            ):
                return DEFAULT_EVM_DECODING_OUTPUT

            position_id = int.from_bytes(context.tx_log.data[32:64])
            token = self.base.get_or_create_evm_token(
                address=bytes_to_address(context.tx_log.data[128:160]),
            )
            amount = token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[160:192]),
                token=token,
            )
            self._transform_matching_event(
                context=context,
                from_event_type=HistoryEventType.RECEIVE,
                token=token,
                amount=amount,
                allowed_labels=(divestor,),
                allowed_addresses=self.deployment.collateral_wrappers | {self.deployment.put_manager},  # noqa: E501
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                notes=f'Divest {amount} {token.symbol} from {FLYING_TULIP_LABEL} put position #{position_id}',  # noqa: E501
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == UNSTAKE_TOPIC:  # Withdraw(address,uint256,uint256)
            if not self.base.is_tracked(
                owner := bytes_to_address(context.tx_log.data[0:32]),
            ):
                return DEFAULT_EVM_DECODING_OUTPUT

            position_id = int.from_bytes(context.tx_log.data[32:64])
            ft_token = self.base.get_or_create_evm_token(address=self.deployment.ft_token)
            amount = token_normalized_value(
                token_amount=int.from_bytes(context.tx_log.data[64:96]),
                token=ft_token,
            )
            self._transform_matching_event(
                context=context,
                from_event_type=HistoryEventType.RECEIVE,
                token=ft_token,
                amount=amount,
                allowed_labels=(owner,),
                allowed_addresses=(self.deployment.put_manager,),
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                notes=f'Withdraw {amount} FT from {FLYING_TULIP_LABEL} put position #{position_id}',  # noqa: E501
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.deployment.put_manager: (self._decode_put_manager,)}
