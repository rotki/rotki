from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.stakedao.decoder import StakedaoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

from .constants import (
    STAKEDAO_CLAIMER1,
    STAKEDAO_CLAIMER2,
    STAKEDAO_CLAIMER_OLD,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class StakedaoDecoder(StakedaoCommonDecoder):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            claim_bribe_addresses={STAKEDAO_CLAIMER_OLD},
            claim_bounty_addresses={
                STAKEDAO_CLAIMER1,
                STAKEDAO_CLAIMER2,
                string_to_evm_address('0x7D0F747eb583D43D41897994c983F13eF7459e1f'),
                string_to_evm_address('0x00000004E4FB0C3017b543EF66cC8A89F5dE74Ff'),
                string_to_evm_address('0x0000000446b28e4c90DbF08Ead10F3904EB27606'),
                string_to_evm_address('0x000000060e56DEfD94110C1a9497579AD7F5b254'),
                string_to_evm_address('0x000000071a273073c824E2a8B0192963e0eEA68b'),
                string_to_evm_address('0x00000007D987c2Ea2e02B48be44EC8F92B8B06e8'),
                string_to_evm_address('0x00000000d0FFb95412346C83F12D0697E4dD2255'),
                string_to_evm_address('0x000000069feD904D94e72202BDC417b19993e18D'),
            },
        )
