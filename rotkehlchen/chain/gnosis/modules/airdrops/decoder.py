import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.cowswap.constants import COWSWAP_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.cowswap.interfaces import CowswapAirdropDecoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.assets import A_GNOSIS_VCOW
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AirdropsDecoder(CowswapAirdropDecoder):

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
            vcow=A_GNOSIS_VCOW,
        )

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (COWSWAP_CPT_DETAILS,)
