from typing import Optional, TypedDict

from rotkehlchen.types import SUPPORTED_CHAIN_IDS, EVMTxHash


class EvmTransactionDecodingApiData(TypedDict):
    evm_chain: SUPPORTED_CHAIN_IDS
    tx_hashes: Optional[list[EVMTxHash]]
