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
] + list(SUPPORTED_BLOCKCHAIN_TO_CHAINID.keys()) + list(SUPPORTED_EVMLIKE_CHAINS)
