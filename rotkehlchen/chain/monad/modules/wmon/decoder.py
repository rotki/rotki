from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.weth.decoder import WethDecoderBase
from rotkehlchen.chain.monad.modules.wmon.constants import CPT_WMON
from rotkehlchen.constants.assets import A_MON, A_WMON

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.monad.node_inquirer import MonadInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class WmonDecoder(WethDecoderBase):
    def __init__(
            self,
            monad_inquirer: 'MonadInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=monad_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            base_asset=A_MON.resolve_to_crypto_asset(),
            wrapped_token=A_WMON.resolve_to_evm_token(),
            counterparty=CPT_WMON,
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_WMON, label='WMON', image='wmon.svg'),)
