"""Registry between supported chains and their locations in the location tree"""
from typing import TYPE_CHECKING, Final

from rotkehlchen.locations.constants import (
    LOCATION_ARBITRUM_ONE,
    LOCATION_AVALANCHE,
    LOCATION_BASE,
    LOCATION_BINANCE_SC,
    LOCATION_BITCOIN,
    LOCATION_BITCOIN_CASH,
    LOCATION_ETHEREUM,
    LOCATION_GNOSIS,
    LOCATION_HYPERLIQUID,
    LOCATION_INK,
    LOCATION_KUSAMA,
    LOCATION_MONAD,
    LOCATION_OPTIMISM,
    LOCATION_POLKADOT,
    LOCATION_POLYGON_POS,
    LOCATION_ROBINHOOD,
    LOCATION_SCROLL,
    LOCATION_SOLANA,
    LOCATION_SONIC,
    LOCATION_ZKSYNC_LITE,
)
from rotkehlchen.types import (
    CHAINS_WITH_TRANSACTIONS,
    CHAINS_WITH_TRANSACTIONS_TYPE,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    ChainID,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.locations.types import LocationIdentifier

EVM_CHAIN_ID_TO_LOCATION: Final[dict[ChainID, LocationIdentifier]] = {
    ChainID.ETHEREUM: LOCATION_ETHEREUM,
    ChainID.OPTIMISM: LOCATION_OPTIMISM,
    ChainID.POLYGON_POS: LOCATION_POLYGON_POS,
    ChainID.ARBITRUM_ONE: LOCATION_ARBITRUM_ONE,
    ChainID.BASE: LOCATION_BASE,
    ChainID.HYPERLIQUID: LOCATION_HYPERLIQUID,
    ChainID.GNOSIS: LOCATION_GNOSIS,
    ChainID.SCROLL: LOCATION_SCROLL,
    ChainID.BINANCE_SC: LOCATION_BINANCE_SC,
    ChainID.MONAD: LOCATION_MONAD,
    ChainID.SONIC: LOCATION_SONIC,
    ChainID.ROBINHOOD: LOCATION_ROBINHOOD,
    ChainID.INK: LOCATION_INK,
}
_LOCATION_TO_EVM_CHAIN_ID: Final = {location: chain_id for chain_id, location in EVM_CHAIN_ID_TO_LOCATION.items()}  # noqa: E501

EVM_LOCATIONS: Final = tuple(EVM_CHAIN_ID_TO_LOCATION.values())
EVMLIKE_LOCATIONS: Final = (LOCATION_ZKSYNC_LITE,)
EVM_EVMLIKE_LOCATIONS: Final = EVM_LOCATIONS + EVMLIKE_LOCATIONS
BITCOIN_LOCATIONS: Final = (LOCATION_BITCOIN, LOCATION_BITCOIN_CASH)

_CHAIN_TO_LOCATION: Final[dict[SupportedBlockchain, LocationIdentifier]] = {
    **{chain_id.to_blockchain(): location for chain_id, location in EVM_CHAIN_ID_TO_LOCATION.items()},  # noqa: E501
    SupportedBlockchain.ZKSYNC_LITE: LOCATION_ZKSYNC_LITE,
    SupportedBlockchain.BITCOIN: LOCATION_BITCOIN,
    SupportedBlockchain.BITCOIN_CASH: LOCATION_BITCOIN_CASH,
    SupportedBlockchain.SOLANA: LOCATION_SOLANA,
}
BLOCKCHAIN_LOCATIONS: Final = EVM_EVMLIKE_LOCATIONS + BITCOIN_LOCATIONS + (LOCATION_SOLANA,)
_BALANCES_CHAIN_TO_LOCATION: Final[dict[SupportedBlockchain, LocationIdentifier]] = {
    **_CHAIN_TO_LOCATION,
    SupportedBlockchain.ETHEREUM_BEACONCHAIN: LOCATION_ETHEREUM,
    SupportedBlockchain.KUSAMA: LOCATION_KUSAMA,
    SupportedBlockchain.POLKADOT: LOCATION_POLKADOT,
    SupportedBlockchain.AVALANCHE: LOCATION_AVALANCHE,
}


def location_from_chain_id(chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE) -> LocationIdentifier:
    return EVM_CHAIN_ID_TO_LOCATION[chain_id]


def location_of_chain_balances(chain: SupportedBlockchain) -> LocationIdentifier:
    """The location holding the balances of a chain's accounts. Validator balances of the
    beacon chain are ETH of Ethereum Mainnet, so they belong to Ethereum."""
    return _BALANCES_CHAIN_TO_LOCATION[chain]


def location_to_chain_id(location: LocationIdentifier) -> int:
    """The EVM chain id of an EVM location. Returns the plain int since that is how it is
    mostly used. May raise KeyError for a location that is not an EVM chain."""
    return _LOCATION_TO_EVM_CHAIN_ID[location].value


def location_from_chain(chain: CHAINS_WITH_TRANSACTIONS_TYPE) -> LocationIdentifier:
    assert chain in CHAINS_WITH_TRANSACTIONS, f'Got in location_from_chain for {chain}'
    return _CHAIN_TO_LOCATION[chain]


def is_evm_location(location: str) -> bool:
    return location in EVM_LOCATIONS


def is_evmlike_location(location: str) -> bool:
    return location in EVMLIKE_LOCATIONS


def is_evm_or_evmlike_location(location: str) -> bool:
    return location in EVM_EVMLIKE_LOCATIONS


def is_bitcoin_location(location: str) -> bool:
    return location in BITCOIN_LOCATIONS


_LOCATION_TO_CHAIN: Final = {location: chain for chain, location in _CHAIN_TO_LOCATION.items()}


def location_to_chain(location: str) -> SupportedBlockchain:
    """The chain of a blockchain location. May raise KeyError for any other location."""
    return _LOCATION_TO_CHAIN[location]  # type: ignore[index]  # plain str lookups are fine
