from enum import Enum


class NodeName(Enum):
    OWN = 0
    ETHERSCAN = 1
    MYCRYPTO = 2
    BLOCKSCOUT = 3
    AVADO_POOL = 4

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

        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')
