from dataclasses import dataclass, field
from typing import NamedTuple, Optional, overload

from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.types import (
    SUPPORTED_EVM_CHAINS,
    BlockchainAddress,
    BTCAddress,
    ChecksumEvmAddress,
    ListOfBlockchainAddresses,
    SupportedBlockchain,
)


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=False, frozen=False)
class BlockchainAccounts:
    eth: list[ChecksumEvmAddress] = field(default_factory=list)
    optimism: list[ChecksumEvmAddress] = field(default_factory=list)
    btc: list[BTCAddress] = field(default_factory=list)
    bch: list[BTCAddress] = field(default_factory=list)
    ksm: list[SubstrateAddress] = field(default_factory=list)
    dot: list[SubstrateAddress] = field(default_factory=list)
    avax: list[ChecksumEvmAddress] = field(default_factory=list)

    @overload
    def get(self, blockchain: SUPPORTED_EVM_CHAINS) -> list[ChecksumEvmAddress]:
        ...

    @overload
    def get(self, blockchain: SupportedBlockchain) -> ListOfBlockchainAddresses:
        ...

    def get(self, blockchain: SupportedBlockchain) -> ListOfBlockchainAddresses:
        return getattr(self, blockchain.get_key())


class BlockchainAccountData(NamedTuple):
    address: BlockchainAddress
    label: Optional[str] = None
    tags: Optional[list[str]] = None
