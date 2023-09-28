import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import GovernableDecoderInterface
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, DecoderEventMappingType

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

GOVERNOR_ADDRESS = string_to_evm_address('0xcDF27F107725988f2261Ce2256bDfCdE8B382B10')


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismGovernorDecoder(GovernableDecoderInterface):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            protocol=CPT_OPTIMISM,
            proposals_url='https://vote.optimism.io/proposals',
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GOVERNOR_ADDRESS: (self._decode_vote_cast,),
        }

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_OPTIMISM: {
            HistoryEventType.INFORMATIONAL: {
                HistoryEventSubType.GOVERNANCE: EventCategory.GOVERNANCE,
            },
        }}

    def counterparties(self) -> list[CounterpartyDetails]:
        return [OPTIMISM_CPT_DETAILS]
