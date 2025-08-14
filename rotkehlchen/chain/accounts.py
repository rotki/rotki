from dataclasses import dataclass, field
from typing import Any, Generic, NamedTuple, overload

from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.types import (
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    AnyBlockchainAddress,
    BlockchainAddress,
    BTCAddress,
    ChecksumEvmAddress,
    SupportedBlockchain,
    TuplesOfBlockchainAddresses,
)


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=False, frozen=True)
class BlockchainAccounts:
    eth: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    optimism: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    polygon_pos: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    arbitrum_one: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    base: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    gnosis: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    scroll: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    binance_sc: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    btc: tuple[BTCAddress, ...] = field(default_factory=tuple)
    bch: tuple[BTCAddress, ...] = field(default_factory=tuple)
    ksm: tuple[SubstrateAddress, ...] = field(default_factory=tuple)
    dot: tuple[SubstrateAddress, ...] = field(default_factory=tuple)
    avax: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)
    zksync_lite: tuple[ChecksumEvmAddress, ...] = field(default_factory=tuple)

    @overload
    def get(self, blockchain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE) -> tuple[ChecksumEvmAddress, ...]:
        ...

    @overload
    def get(self, blockchain: SupportedBlockchain) -> TuplesOfBlockchainAddresses:
        ...

    def get(self, blockchain: SupportedBlockchain) -> TuplesOfBlockchainAddresses:
        return getattr(self, blockchain.get_key())

    def add(self, blockchain: SupportedBlockchain, address: BlockchainAddress) -> None:
        """Adds an address to the given blockchain set of addresses"""
        bkey = blockchain.get_key()
        current_addresses = getattr(self, bkey)
        # class is frozen to disallow arbitrarily changing the tuple. But here we do it knowingly
        object.__setattr__(self, bkey, current_addresses + (address,))

    def remove(self, blockchain: SupportedBlockchain, address: BlockchainAddress) -> None:
        """Removes an address from the given blockchain set of addresses"""
        bkey = blockchain.get_key()
        current_addresses = getattr(self, bkey)
        # class is frozen to disallow arbitrarily changing the tuple. But here we do it knowingly
        object.__setattr__(self, bkey, tuple(x for x in current_addresses if x != address))


class OptionalBlockchainAccount(NamedTuple):
    """Represents a blockchain account with an optional chain specification."""
    chain: SupportedBlockchain | None
    address: BlockchainAddress


class BlockchainAccountData(NamedTuple):
    chain: SupportedBlockchain
    address: BlockchainAddress
    label: str | None = None
    tags: list[str] | None = None


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SingleBlockchainAccountData(Generic[AnyBlockchainAddress]):
    address: AnyBlockchainAddress
    label: str | None = None
    tags: list[str] | None = None

    def serialize(self) -> dict[str, Any]:
        return {'address': self.address, 'label': self.label, 'tags': self.tags}

    def to_blockchain_account_data(self, chain: SupportedBlockchain) -> BlockchainAccountData:
        return BlockchainAccountData(
            chain=chain,
            address=self.address,
            label=self.label,
            tags=self.tags,
        )
