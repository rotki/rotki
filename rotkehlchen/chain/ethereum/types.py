from enum import Enum
from typing import Any, List, NamedTuple

from eth_typing import HexAddress, HexStr

from rotkehlchen.types import ChecksumEthAddress


def string_to_ethereum_address(value: str) -> ChecksumEthAddress:
    """This is a conversion without any checks of a string to ethereum address

    Is only used for typing.
    """
    return ChecksumEthAddress(HexAddress(HexStr(value)))


class NodeName(Enum):
    """Various node types

    Some open nodes taken from here: https://ethereumnodes.com/
    Related issue: https://github.com/rotki/rotki/issues/1716
    """
    OWN = 0
    ETHERSCAN = 1
    MYCRYPTO = 2
    BLOCKSCOUT = 3
    AVADO_POOL = 4
    ONEINCH = 5
    MYETHERWALLET = 6
    LINKPOOL = 7
    CLOUDFLARE_ETH = 8

    def __str__(self) -> str:
        if self == NodeName.OWN:
            return 'own node'
        if self == NodeName.ETHERSCAN:
            return 'etherscan'
        if self == NodeName.MYCRYPTO:
            return 'mycrypto'
        if self == NodeName.BLOCKSCOUT:
            return 'blockscout'
        if self == NodeName.AVADO_POOL:
            return 'avado pool'
        if self == NodeName.ONEINCH:
            return '1inch'
        if self == NodeName.MYETHERWALLET:
            return 'myetherwallet'
        if self == NodeName.LINKPOOL:
            return 'linkpool'
        if self == NodeName.CLOUDFLARE_ETH:
            return 'cloudflare-eth'
        # else
        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')

    def endpoint(self, own_rpc_endpoint: str) -> str:
        if self == NodeName.OWN:
            return own_rpc_endpoint
        if self == NodeName.ETHERSCAN:
            raise TypeError('Called endpoint for etherscan')
        if self == NodeName.MYCRYPTO:
            return 'https://api.mycryptoapi.com/eth'
        if self == NodeName.BLOCKSCOUT:
            return 'https://mainnet-nethermind.blockscout.com/'
        if self == NodeName.AVADO_POOL:
            return 'https://mainnet.eth.cloud.ava.do/'
        if self == NodeName.ONEINCH:
            return 'https://web3.1inch.exchange'
        if self == NodeName.MYETHERWALLET:
            return 'https://nodes.mewapi.io/rpc/eth'
        if self == NodeName.LINKPOOL:
            return 'https://main-rpc.linkpool.io/'
        if self == NodeName.CLOUDFLARE_ETH:
            return 'https://cloudflare-eth.com/'
        # else
        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')


class EnsContractParams(NamedTuple):
    """Parameters for a contract"""

    address: ChecksumEthAddress
    abi: List[Any]
    method_name: str
    arguments: List[Any]
