from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.spark.lend.decoder import SparklendCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class SparklendDecoder(SparklendCommonDecoder):
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
            pool_addresses=(string_to_evm_address('0x2Dae5307c5E3FD1CF5A72Cb6F698f915860607e0'),),
            native_gateways=(string_to_evm_address('0xBD7D6a9ad7865463DE44B05F04559f65e3B11704'),),
            treasury=string_to_evm_address('0xb9E6DBFa4De19CCed908BcbFe1d015190678AB5f'),
            incentives=string_to_evm_address('0x98e6BcBA7d5daFbfa4a92dAF08d3d7512820c30C'),
        )
