import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_CPT_DETAILS, CPT_ARBITRUM_ONE
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


GOVERNOR_ADDRESS = string_to_evm_address('0xf07DeD9dC292157749B6Fd268E37DF6EA38395B9')
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ArbitrumGovernorDecoder(GovernableDecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_ARBITRUM_ONE,
            proposals_url='https://www.tally.xyz/gov/arbitrum/proposal',
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {GOVERNOR_ADDRESS: (self._decode_vote_cast,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ARBITRUM_ONE_CPT_DETAILS,)
