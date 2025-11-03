from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.decoding.interfaces import DecoderInterface
from rotkehlchen.types import SolanaAddress

from .structures import SolanaDecodingOutput, SolanaEventDecoderContext

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.user_messages import MessagesAggregator

    from .tools import SolanaDecoderTools


class SolanaDecoderInterface(DecoderInterface[SolanaAddress, 'SolanaInquirer', 'SolanaDecoderTools'], ABC):  # noqa: E501

    def __init__(
            self,
            node_inquirer: 'SolanaInquirer',
            base_tools: 'SolanaDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            node_inquirer=node_inquirer,
            base_tools=base_tools,
        )
        self.msg_aggregator = msg_aggregator

    def transfer_addresses_to_decoders(self) -> dict[
        SolanaAddress,
        tuple[Callable[[SolanaEventDecoderContext], SolanaDecodingOutput], ...],
    ]:
        """Subclasses may implement this to return the mappings of from/to transfer addresses
        to corresponding decoder functions. These are run immediately after the basic transfer
        decoding is finished.
        """
        return {}
