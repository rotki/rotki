from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.morpho.decoder import MorphoCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MorphoDecoder(MorphoCommonDecoder):

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
            bundlers={
                string_to_evm_address('0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077'),  # EthereumBundlerV2  # noqa: E501
                string_to_evm_address('0xa7995f71aa11525db02fc2473c37dee5dbf55107'),  # EthereumBundler  # noqa: E501
                string_to_evm_address('0xb3dcc75db379925edfd3007511a8ce0cb4aa8e76'),  # AaveV2MigrationBundler  # noqa: E501
                string_to_evm_address('0x98ccb155e86bb478d514a827d16f58c6912f9bdc'),  # AaveV3MigrationBundler  # noqa: E501
                string_to_evm_address('0x16f38d2e764e7bebf625a8e995b34968226d2f9c'),  # AaveV3OptimizerMigrationBundler  # noqa: E501
                string_to_evm_address('0x26bf52a84360ad3d01d7cdc28fc2ddc04d8c8647'),  # CompoundV2MigrationBundler  # noqa: E501
                string_to_evm_address('0x3a0e2e9fb9c95fbc843daf166276c90b6c479558'),  # CompoundV3MigrationBundler  # noqa: E501
            },
            rewards_distributors=[
                string_to_evm_address('0x330eefa8a787552DC5cAd3C3cA644844B1E61Ddb'),
                string_to_evm_address('0x678dDC1d07eaa166521325394cDEb1E4c086DF43'),
                string_to_evm_address('0x2EfD4625d0c149EbADf118EC5446c6de24d916A4'),
                string_to_evm_address('0xfD9B178257ae397a674698834628262fd858aaD3'),
                string_to_evm_address('0xB5b17231E2C89Ca34CE94B8CB895A9B124BB466e'),
                string_to_evm_address('0x7815CAb40D9b83021f55418a013cceC3813646FB'),
                string_to_evm_address('0xfD5Ee44774a162Ec25Dbf3a4cFf6242A1fA5E338'),
            ],
            weth=A_WETH,
        )
