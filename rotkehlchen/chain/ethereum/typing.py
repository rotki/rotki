from enum import Enum


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
        elif self == NodeName.ETHERSCAN:
            return 'etherscan'
        elif self == NodeName.MYCRYPTO:
            return 'mycrypto'
        elif self == NodeName.BLOCKSCOUT:
            return 'blockscout'
        elif self == NodeName.AVADO_POOL:
            return 'avado pool'
        elif self == NodeName.ONEINCH:
            return '1inch'
        elif self == NodeName.MYETHERWALLET:
            return 'myetherwallet'
        elif self == NodeName.LINKPOOL:
            return 'linkpool'
        elif self == NodeName.CLOUDFLARE_ETH:
            return 'cloudflare-eth'

        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')

    def endpoint(self, own_rpc_endpoint: str) -> str:
        if self == NodeName.OWN:
            return own_rpc_endpoint
        elif self == NodeName.ETHERSCAN:
            raise TypeError('Called endpoint for etherscan')
        elif self == NodeName.MYCRYPTO:
            return 'https://api.mycryptoapi.com/eth'
        elif self == NodeName.BLOCKSCOUT:
            return 'https://mainnet-nethermind.blockscout.com/'
        elif self == NodeName.AVADO_POOL:
            return 'https://mainnet.eth.cloud.ava.do/'
        elif self == NodeName.ONEINCH:
            return 'https://web3.1inch.exchange'
        elif self == NodeName.MYETHERWALLET:
            return 'https://nodes.mewapi.io/rpc/eth'
        elif self == NodeName.LINKPOOL:
            return 'https://main-rpc.linkpool.io/'
        elif self == NodeName.CLOUDFLARE_ETH:
            return 'https://cloudflare-eth.com/'

        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')
