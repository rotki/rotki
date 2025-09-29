from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoderBase
from rotkehlchen.chain.gnosis.modules.wxdai.constants import CPT_WXDAI
from rotkehlchen.constants.assets import A_WXDAI, A_XDAI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class WxdaiDecoder(WethDecoderBase):
    def __init__(
            self,
            gnosis_inquirer: 'GnosisInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=gnosis_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            base_asset=A_XDAI.resolve_to_crypto_asset(),
            wrapped_token=A_WXDAI.resolve_to_evm_token(),
            counterparty=CPT_WXDAI,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_WXDAI, label='WXDAI', image='wxdai.png'),)
