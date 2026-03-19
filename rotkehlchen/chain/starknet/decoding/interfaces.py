from abc import ABC
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.interfaces import DecoderInterface
from rotkehlchen.types import StarknetAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.starknet.node_inquirer import StarknetInquirer
    from rotkehlchen.user_messages import MessagesAggregator

    from .tools import StarknetDecoderTools


class StarknetDecoderInterface(DecoderInterface[StarknetAddress, 'StarknetInquirer', 'StarknetDecoderTools'], ABC):  # noqa: E501

    def __init__(
            self,
            node_inquirer: 'StarknetInquirer',
            base_tools: 'StarknetDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            base_tools=base_tools,
        )
        self.msg_aggregator = msg_aggregator
