from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.types import (
    SUPPORTED_BLOCKCHAIN_TO_CHAINID,
    SUPPORTED_EVMLIKE_CHAINS,
    SupportedBlockchain,
)

DEFAULT_EVM_RPC_TIMEOUT = 10
NON_BITCOIN_CHAINS = [
    SupportedBlockchain.AVALANCHE,
    SupportedBlockchain.POLKADOT,
    SupportedBlockchain.ETHEREUM_BEACONCHAIN,
    SupportedBlockchain.KUSAMA,
    SupportedBlockchain.SOLANA,
] + list(SUPPORTED_BLOCKCHAIN_TO_CHAINID.keys()) + list(SUPPORTED_EVMLIKE_CHAINS)


SAFE_BASIC_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'getChainId',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [],
        'name': 'VERSION',
        'outputs': [{'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [],
        'name': 'getThreshold',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]
