from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.eas.decoder import EASCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class EasDecoder(EASCommonDecoder):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            attestation_service_address=string_to_evm_address('0xbD75f629A22Dc1ceD33dDA0b68c546A1c035c458'),
        )
