from typing import Optional, TypedDict

from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChecksumEvmAddress, EVMTxHash


class EvmTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS
    tx_hashes: Optional[list[EVMTxHash]]


class EvmPendingTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS
    addresses: Optional[list[ChecksumEvmAddress]]
