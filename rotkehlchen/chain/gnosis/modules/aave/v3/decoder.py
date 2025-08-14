from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v3.decoder import Aavev3LikeCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev3Decoder(Aavev3LikeCommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'GnosisInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0xb50201558B00496A145fE76f7424749556E326D8'),),
            native_gateways=(
                string_to_evm_address('0xfE76366A986B72c3f2923e05E6ba07b7de5401e4'),
                string_to_evm_address('0x721B9abAb6511b46b9ee83A1aba23BDAcB004149'),
            ),
            treasury=string_to_evm_address('0x3e652E97ff339B73421f824F5b03d75b62F1Fb51'),
            incentives=string_to_evm_address('0xaD4F91D26254B6B0C6346b390dDA2991FDE2F20d'),
            collateral_swap_address=string_to_evm_address('0x63dfa7c09Dc2Ff4030d6B8Dc2ce6262BF898C8A4'),
        )
