from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.giveth.decoder import GivethDonationDecoderBase

from .constants import GIVETH_DONATION_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class GivethDecoder(GivethDonationDecoderBase):

    def __init__(  # pylint: disable=super-init-not-called
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            donation_contract_address=GIVETH_DONATION_CONTRACT_ADDRESS,
        )
