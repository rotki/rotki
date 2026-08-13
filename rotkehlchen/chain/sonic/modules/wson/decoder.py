from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoderBase
from rotkehlchen.chain.sonic.modules.wson.constants import CPT_WSON
from rotkehlchen.constants.assets import A_S, A_WS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.sonic.node_inquirer import SonicInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class WsonDecoder(WethDecoderBase):
    def __init__(
            self,
            sonic_inquirer: SonicInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=sonic_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            base_asset=A_S.resolve_to_crypto_asset(),
            wrapped_token=A_WS.resolve_to_evm_token(),
            counterparty=CPT_WSON,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_WSON, label='WS', image='wson.svg'),)
