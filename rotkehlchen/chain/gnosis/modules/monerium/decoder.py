from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.monerium.decoder import MoneriumCommonDecoder
from rotkehlchen.chain.gnosis.modules.monerium.constants import GNOSIS_MONERIUM_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class MoneriumDecoder(MoneriumCommonDecoder):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            monerium_token_addresses=GNOSIS_MONERIUM_ADDRESSES,
        )

    def _v1_to_v2_migration_hashes(self) -> set[str]:
        return {
            '0x3d64da1ffb038e3c76ab895d151d9823350f183f2821c9bd2ab49fc0ee583e93',
            '0x0a0512e14bb3b78571b1ffaafa6b7933021a091ee1b6b6a0a3197a0122365619',
            '0x58c0542152e9692b686467b59c52c56e5389d5b3bdda38fe406bd71dac34ce46',
            '0xbb10a17313af72d5e319172e52819835553288f4e802c2e0f3d89530831f6dd2',
            '0xa8b2dbdeb4b1d5e954bd3143bbaa3d4bc677950e24befb34d942bcdda4b94d73',
            '0xa32445accf1b8c29d6e9be1f65b5ae78f0d2eb117cb397234e588c53dfa313da',
            '0x4a9f118f05f99bdb720978470e677826197a4af31e07eb04ca7858e49c117f67',
            '0x31770f06e3dfc1e19f08c9274358b21b5cd22cb902e749207fc3db32c4b599d4',
            '0xd8da5d945bfabb40e73378f321f304bd5c65c16b5d43cc188bd6b2eaef33e9f5',
            '0x7b5d5e17ccd4beea282683842a14e1f5f168c8051aab0a107fa8bce079fbfa8d',
            '0xc076a3792a995caddd5b50a92e0affeed8ed1ef631865bbc17945de9c7fa6bed',
            '0x22b68af1d5596afb4f89fa3167f92f03dae86b61c591cef99223764a1af3f889',
            '0xe75f2f82538295a54725cc51426c3e19a483991e8451f2d67f7a6f4639cfde56',
            '0x13ca8cb7161b6dff443bd1f7081b7ee36a6e193b64433b73e605494b5d916dfb',
            '0xb82e531328f1cec88d67c0ad3a50cafb97a8eddbf537973fa61b6e1ca232110a',
            '0x9242d2c1f51b55a4af5224db22937dedc02d1b39dea3a3e82373168b6aa03281',
            '0x5d8bc6cb71ae87b6ac3458ef0909581f920beee44870b70bc7a438924e00c664',
            '0x69d9256b0f01a8e605efd822a1358e4ec2fcefc298ce3f42ae9a21c86e72f5a0',
            '0x7bdb042519db39ec01940dd26adc6e25eb6d54d43ed010e8499dd19767dda227',
            '0x6241b6ef81b50e87585741362247852e6b325eb4401e5bde83e6c52ef9f2f097',
            '0xaab0ff0a7f6b52abbef10e32ba7bb71ac0ff89b934f02ac3cc5e765fd0fc4a03',
            '0x8d0716cc5e45ae88f0e1b33c96cadab8ba69d691c4b342c3898323a3d56388fc',
            '0xf56f97e76d1a31de16d413951092c1ddb5195a0ed667757a2171f1b5839aa025',
            '0xf727f40f491ebd885b369491e86a5ddf766856f9f82aa1c3bf5587df5f907093',
            '0x4a77edfadc781c215d886b6e79ad0daaa542196722da2e84895943f29a15de87',
            '0x7aa0914d4b806b7fbfc67f539a6897a6aa221c321e92d8c354d374b3663c09d5',
            '0x180d1bafa634713f30f3a54325e5454e3f72fdb4e92c8a8c0dd3b74a282e1343',
            '0x3d7a6db411ad48a1efef878cdb197a0925c1da864dc3678bf222c28ff0ed0e87',
            '0x5805c0f5e08d7d19d24aeb1f575328362dd403d1dca588068c4beaff8a8eb78a',
        }
