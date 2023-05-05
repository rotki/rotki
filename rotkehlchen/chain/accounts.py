from dataclasses import dataclass, field
from typing import Any, Generic, NamedTuple, Optional, overload

from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.types import (
    SUPPORTED_EVM_CHAINS,
    AnyBlockchainAddress,
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
    chain: SupportedBlockchain
    address: BlockchainAddress
    label: Optional[str] = None
    tags: Optional[list[str]] = None


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SingleBlockchainAccountData(Generic[AnyBlockchainAddress]):
    address: AnyBlockchainAddress
    label: Optional[str] = None
    tags: Optional[list[str]] = None

    def serialize(self) -> dict[str, Any]:
        return {'address': self.address, 'label': self.label, 'tags': self.tags}

    def to_blockchain_account_data(self, chain: SupportedBlockchain) -> BlockchainAccountData:
        return BlockchainAccountData(
            chain=chain,
            address=self.address,
            label=self.label,
            tags=self.tags,
        )
