from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import BASE_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.superchain_bridge.l1.decoder import (
    SuperchainL1SideCommonBridgeDecoder,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

OPTIMISM_PORTAL_ADDRESS: Final = string_to_evm_address('0xbEb5Fc579115071764c7423A4f12eDde41f106Ed')  # noqa: E501


class SuperchainBridgebaseDecoder(SuperchainL1SideCommonBridgeDecoder):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            bridge_addresses=(string_to_evm_address('0x3154Cf16ccdb4C6d922629664174b904d80F2C35'),),
            l2_chain=ChainID.BASE,
            counterparty=BASE_CPT_DETAILS,
        )

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (BASE_CPT_DETAILS,)
