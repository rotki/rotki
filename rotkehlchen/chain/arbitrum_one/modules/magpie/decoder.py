from typing import Any

from rotkehlchen.chain.evm.decoding.magpie.decoder import MagpieCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address


class MagpieDecoder(MagpieCommonDecoder):
    def __init__(
            self,
            evm_inquirer: Any,
            base_tools: Any,
            msg_aggregator: Any,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            router_address=string_to_evm_address('0x34CdCe58CBdC6C54f2AC808A24561D0AB18Ca8Be'),
        )
