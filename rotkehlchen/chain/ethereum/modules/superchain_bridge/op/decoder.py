from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.constants import OPTIMISM_CPT_DETAILS
from rotkehlchen.chain.evm.decoding.superchain_bridge.l1.decoder import (
    SuperchainL1SideCommonBridgeDecoder,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


OPTIMISM_PORTAL_ADDRESS: Final = string_to_evm_address('0xbEb5Fc579115071764c7423A4f12eDde41f106Ed')  # noqa: E501


class SuperchainBridgeopDecoder(SuperchainL1SideCommonBridgeDecoder):
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
            bridge_addresses=(
                string_to_evm_address('0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1'),
                string_to_evm_address('0x10E6593CDda8c58a1d0f14C5164B376352a55f2F'),
                string_to_evm_address('0xbEb5Fc579115071764c7423A4f12eDde41f106Ed'),
                string_to_evm_address('0x467194771dAe2967Aef3ECbEDD3Bf9a310C76C65'),
            ),
            l2_chain=ChainID.OPTIMISM,
            counterparty=OPTIMISM_CPT_DETAILS,
        )

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        entries = super().addresses_to_decoders()
        entries[OPTIMISM_PORTAL_ADDRESS] = (self._decode_prove_withdrawal, )

        return entries

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (OPTIMISM_CPT_DETAILS,)
