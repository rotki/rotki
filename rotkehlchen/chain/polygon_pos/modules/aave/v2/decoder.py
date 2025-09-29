from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.aave.v2.decoder import Aavev2CommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.modules.aave.constants import V3_MIGRATION_HELPER

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.user_messages import MessagesAggregator


class Aavev2Decoder(Aavev2CommonDecoder):

    def __init__(
            self,
            evm_inquirer: 'PolygonPOSInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            pool_addresses=(string_to_evm_address('0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf'),),
            native_gateways=(string_to_evm_address('0xf1e6d4347105138B51E2bacA9A22fA228309ebB1'),),
            incentives=string_to_evm_address('0x357D51124f59836DeD84c8a1730D72B749d8BC23'),
            incentives_reward_token=string_to_evm_address('0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'),  # wrapped Matic  # noqa: E501
            v3_migration_helper=V3_MIGRATION_HELPER,
        )
