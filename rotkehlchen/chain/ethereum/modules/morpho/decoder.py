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
                string_to_evm_address('0x6566194141eefa99Af43Bb5Aa71460Ca2Dc90245'),  # EthereumBundlerV3  # noqa: E501
                string_to_evm_address('0x4095F064B8d3c3548A3bebfd0Bbfd04750E30077'),  # EthereumBundlerV2  # noqa: E501
                string_to_evm_address('0xa7995f71aa11525DB02Fc2473c37Dee5dbf55107'),  # EthereumBundler  # noqa: E501
                string_to_evm_address('0xb3dCc75DB379925edFd3007511A8CE0cB4aa8e76'),  # AaveV2MigrationBundler  # noqa: E501
                string_to_evm_address('0x98ccB155E86bb478d514a827d16f58c6912f9BDC'),  # AaveV3MigrationBundler  # noqa: E501
                string_to_evm_address('0x16F38d2E764E7BeBF625a8E995b34968226D2F9c'),  # AaveV3OptimizerMigrationBundler  # noqa: E501
                string_to_evm_address('0x26bF52a84360Ad3d01d7CDc28FC2dDC04d8c8647'),  # CompoundV2MigrationBundler  # noqa: E501
                string_to_evm_address('0x3a0e2E9FB9c95fBc843daF166276C90B6C479558'),  # CompoundV3MigrationBundler  # noqa: E501
            },
            adapters={
                string_to_evm_address('0x4A6c312ec70E8747a587EE860a0353cd42Be0aE0'),  # GeneralAdapter1  # noqa: E501
                string_to_evm_address('0xf83D17dFE160597b19e4FdD8ea61A23e9a87F962'),  # ERC20WrapperAdapter  # noqa: E501
                string_to_evm_address('0x03b5259Bd204BfD4A616E5B79b0B786d90c6C38f'),  # ParaswapAdapter  # noqa: E501
            },
            weth=A_WETH,
        )
