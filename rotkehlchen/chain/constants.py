from rotkehlchen.types import SupportedBlockchain

DEFAULT_EVM_RPC_TIMEOUT = 10
NON_BITCOIN_CHAINS = (
    SupportedBlockchain.AVALANCHE,
    SupportedBlockchain.POLKADOT,
    SupportedBlockchain.ETHEREUM,
    SupportedBlockchain.ETHEREUM_BEACONCHAIN,
    SupportedBlockchain.KUSAMA,
)
