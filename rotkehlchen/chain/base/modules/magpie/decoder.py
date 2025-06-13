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
            router_addresses=[
                string_to_evm_address('0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B'),  # v3.0
                string_to_evm_address('0x5E766616AaBFB588E23a8EA854e9dbd1042afFD3'),  # v3.1
            ],
        )
