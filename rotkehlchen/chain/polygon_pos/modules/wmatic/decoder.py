from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoderBase
from rotkehlchen.chain.polygon_pos.modules.wmatic.constants import CPT_WMATIC
from rotkehlchen.constants.assets import A_POLYGON_POS_MATIC, A_WMATIC

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class WmaticDecoder(WethDecoderBase):
    def __init__(
            self,
            polygon_pos_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=polygon_pos_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            base_asset=A_POLYGON_POS_MATIC.resolve_to_crypto_asset(),
            wrapped_token=A_WMATIC.resolve_to_evm_token(),
            counterparty=CPT_WMATIC,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_WMATIC, label='WMatic', image='matic.svg'),)
