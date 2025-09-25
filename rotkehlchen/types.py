import typing
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Generic,
    Literal,
    NamedTuple,
    NewType,
    Optional,
    TypeAlias,
    TypeVar,
    get_args,
)

from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes as Web3HexBytes

from rotkehlchen.chain.solana.validation import is_valid_solana_address
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import AddressNotSupported, InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.utils.hexbytes import HexBytes
from rotkehlchen.utils.mixins.enums import (
    DBCharEnumMixIn,
    SerializableEnumNameMixin,
    SerializableEnumValueMixin,
)

from rotkehlchen.chain.substrate.types import SubstrateAddress  # isort:skip
# Import directly from substrateinterface to avoid cyclic import via our substrate utils
from substrateinterface.utils.ss58 import is_valid_ss58_address

from rotkehlchen.chain.bitcoin.bch.validation import is_valid_bitcoin_cash_address
from rotkehlchen.chain.bitcoin.validation import is_valid_btc_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.drivers.gevent import DBCursor

ModuleName = Literal[
    'makerdao_dsr',
    'makerdao_vaults',
    'uniswap',
    'loopring',
    'eth2',
    'sushiswap',
    'liquity',
    'pickle_finance',
    'nfts',
]

OnlyPurgeableModuleName = Literal[
    'gnosis_pay',  # only to purge DB table
    'cowswap',     # only to purge DB table
]

PurgeableModuleName = ModuleName | OnlyPurgeableModuleName

# TODO: Turn this into some kind of light data structure and not just a mapping
# This is a mapping of module ids to human readable names
AVAILABLE_MODULES_MAP = {
    'makerdao_dsr': 'MakerDAO DSR',
    'makerdao_vaults': 'MakerDAO Vaults',
    'uniswap': 'Uniswap',
    'loopring': 'Loopring',
    'eth2': 'Eth2',
    'sushiswap': 'Sushiswap',
    'liquity': 'Liquity',
    'pickle_finance': 'Pickle Finance',
    'nfts': 'NFTs',
}

DEFAULT_OFF_MODULES = {'makerdao_dsr'}

SPAM_PROTOCOL = 'spam'

T_Timestamp = int
Timestamp = NewType('Timestamp', T_Timestamp)

T_TimestampMS = int
TimestampMS = NewType('TimestampMS', T_TimestampMS)

T_ApiKey = str
ApiKey = NewType('ApiKey', T_ApiKey)

T_ApiSecret = bytes
ApiSecret = NewType('ApiSecret', T_ApiSecret)

T_HexColorCode = str
HexColorCode = NewType('HexColorCode', T_HexColorCode)


class ExternalService(SerializableEnumNameMixin):
    ETHERSCAN = auto()
    CRYPTOCOMPARE = auto()
    BEACONCHAIN = auto()
    LOOPRING = auto()
    OPENSEA = auto()
    BLOCKSCOUT = auto()
    MONERIUM = auto()
    THEGRAPH = auto()
    GNOSIS_PAY = auto()
    OPTIMISM_BLOCKSCOUT = auto()
    POLYGON_POS_BLOCKSCOUT = auto()
    ARBITRUM_ONE_BLOCKSCOUT = auto()
    BASE_BLOCKSCOUT = auto()
    GNOSIS_BLOCKSCOUT = auto()
    DEFILLAMA = auto()
    COINGECKO = auto()
    ALCHEMY = auto()
    SCROLL_BLOCKSCOUT = auto()
    HELIUS = auto()

    def get_chain_for_blockscout(self) -> Optional['ChainID']:
        """If the service is a blockscout service return its chain"""
        return BLOCKSCOUT_TO_CHAINID.get(self)

    def premium_only(self) -> bool:
        return self in {ExternalService.GNOSIS_PAY, ExternalService.MONERIUM}


class ExternalServiceApiCredentials(NamedTuple):
    """Represents Credentials for various External APIs. Etherscan, Cryptocompare e.t.c.

    The Api in question must at least have an API key.
    """
    service: ExternalService
    api_key: ApiKey  # for monerium this is the username
    api_secret: str | None = None  # for monerium this is the password

    def serialize_for_db(self) -> tuple[str, str, str | None]:
        return (self.service.name.lower(), self.api_key, self.api_secret)

    def serialize_for_api(self) -> tuple[str, dict[str, str]]:
        value: dict[str, str]
        if self.service == ExternalService.MONERIUM:
            value = {'username': self.api_key, 'password': self.api_secret}  # type:ignore  # exists
        else:
            value = {'api_key': self.api_key}
        return self.service.name.lower(), value


T_TradePair = str
TradePair = NewType('TradePair', T_TradePair)

ChecksumEvmAddress = ChecksumAddress

T_EVMTxHash = HexBytes
EVMTxHash = NewType('EVMTxHash', T_EVMTxHash)


def deserialize_evm_tx_hash(val: Web3HexBytes | (bytearray | (bytes | str))) -> EVMTxHash:
    """Super lightweight wrapper to forward arguments to HexBytes and return an EVMTxHash

    HexBytes constructor handles the deserialization from whatever is given as input.

    May raise DeserializationError if there is an error at deserialization

    NB: Does not actually check that it's 32 bytes. This should happen at reading
    data from outside such as in the marshmallow field validation
    """
    return EVMTxHash(HexBytes(val))


T_BTCAddress = str
BTCAddress = NewType('BTCAddress', T_BTCAddress)

T_BTCTxHash = str
BTCTxHash = NewType('BTCTxHash', T_BTCTxHash)

T_Eth2PubKey = str
Eth2PubKey = NewType('Eth2PubKey', T_Eth2PubKey)

T_SolanaAddress = str
SolanaAddress = NewType('SolanaAddress', T_SolanaAddress)

BlockchainAddress = BTCAddress | ChecksumEvmAddress | SubstrateAddress | SolanaAddress
AnyBlockchainAddress = TypeVar(
    'AnyBlockchainAddress',
    BTCAddress,
    ChecksumEvmAddress,
    SubstrateAddress,
    SolanaAddress,
)
ListOfBlockchainAddresses = list[BTCAddress] | list[ChecksumEvmAddress] | list[SubstrateAddress] | list[SolanaAddress]  # noqa: E501
TuplesOfBlockchainAddresses = tuple[BTCAddress, ...] | tuple[ChecksumEvmAddress, ...] | tuple[SubstrateAddress, ...] | tuple[SolanaAddress, ...]  # noqa: E501


T_Price = FVal
Price = NewType('Price', T_Price)


class AssetAmount(NamedTuple):
    asset: 'Asset'
    amount: FVal


class ChainID(Enum):
    """This class maps each EVM chain to their chain id. This is used to correctly identify EVM
    assets and use it where these ids are needed.

    This enum implements custom serialization/deserialization so it does not inherit from the
    DBIntEnumMixIn since it may differ a bit. TODO: Try it
    """
    ETHEREUM = 1
    OPTIMISM = 10
    BINANCE_SC = 56
    GNOSIS = 100
    POLYGON_POS = 137
    FANTOM = 250
    BASE = 8453
    ARBITRUM_ONE = 42161
    AVALANCHE = 43114
    CELO = 42220
    ARBITRUM_NOVA = 42170
    CRONOS = 25
    BOBA = 288
    EVMOS = 9001
    POLYGON_ZKEVM = 1101
    ZKSYNC_ERA = 324
    PULSECHAIN = 369
    SCROLL = 534352
    SONIC = 146
    LINEA = 59144

    @classmethod
    def deserialize_from_db(cls, value: int) -> 'ChainID':
        try:
            return cls(value)
        except ValueError as e:
            raise DeserializationError(f'Could not deserialize ChainID from value {value}') from e

    def serialize_for_db(self) -> int:
        return self.value

    def serialize(self) -> int:
        return self.value

    @classmethod
    def deserialize(cls, value: int) -> 'ChainID':
        return cls.deserialize_from_db(value)

    def to_name(self) -> str:
        """The name to be used to/from the api instead of the chain id"""
        return self.name.lower()

    def name_and_label(self) -> tuple[str, str]:
        """Name and label to be used by the frontend

        Also returns the name since the only place where label is currently used
        the name is also needed. To avoid 1 extra call to name"""
        name = self.to_name()
        if self == ChainID.POLYGON_POS:
            label = 'Polygon POS'
        elif self == ChainID.ZKSYNC_ERA:
            label = 'zkSync Era'
        elif self == ChainID.POLYGON_ZKEVM:
            label = 'Polygon zkEVM'
        elif self == ChainID.BINANCE_SC:
            label = 'Binance Smart Chain'
        elif self == ChainID.ARBITRUM_ONE:
            label = 'Arbitrum One'
        elif self == ChainID.ARBITRUM_NOVA:
            label = 'Arbitrum Nova'
        elif self == ChainID.PULSECHAIN:
            label = 'PulseChain'
        else:
            label = name.capitalize()

        return name, label

    def label(self) -> str:
        """A label to be used by the frontend"""
        _, label = self.name_and_label()
        return label

    def __str__(self) -> str:
        return self.to_name()

    @classmethod
    def deserialize_from_name(cls, value: str) -> 'ChainID':
        """May raise DeserializationError if the given value can't be deserialized"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize evm chain value from non string value: {value}',
            )

        upper_value = value.replace(' ', '_').upper()
        try:
            return getattr(cls, upper_value)
        except AttributeError as e:
            raise DeserializationError(f'Failed to deserialize evm chain value {value}') from e

    def to_blockchain(self) -> 'SupportedBlockchain':
        return CHAINID_TO_SUPPORTED_BLOCKCHAIN[self]


SUPPORTED_CHAIN_IDS = Literal[
    ChainID.ETHEREUM,
    ChainID.OPTIMISM,
    ChainID.POLYGON_POS,
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.GNOSIS,
    ChainID.SCROLL,
    ChainID.BINANCE_SC,
]


BLOCKSCOUT_TO_CHAINID = {
    ExternalService.BLOCKSCOUT: ChainID.ETHEREUM,
    ExternalService.OPTIMISM_BLOCKSCOUT: ChainID.OPTIMISM,
    ExternalService.POLYGON_POS_BLOCKSCOUT: ChainID.POLYGON_POS,
    ExternalService.ARBITRUM_ONE_BLOCKSCOUT: ChainID.ARBITRUM_ONE,
    ExternalService.BASE_BLOCKSCOUT: ChainID.BASE,
    ExternalService.GNOSIS_BLOCKSCOUT: ChainID.GNOSIS,
    ExternalService.SCROLL_BLOCKSCOUT: ChainID.SCROLL,
}


class EvmlikeChain(StrEnum):
    """This is an enum for EvmLike chains that are not fully compatible with evm chains.
    For example have no chain id"""
    ZKSYNC_LITE = auto()


class EvmTransactionAuthorization(NamedTuple):
    """EIP-7702 authorization to delegate EOA execution to a contract.

    When applied, sets EOA code to a delegation indicator pointing to the
    delegated address, redirecting all calls to that contract's code.
    """
    nonce: int
    delegated_address: ChecksumEvmAddress


@dataclass(frozen=True)
class EvmTransaction:
    """Represent an EVM transaction"""
    tx_hash: EVMTxHash
    chain_id: ChainID
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEvmAddress
    to_address: ChecksumEvmAddress | None
    value: int
    gas: int
    gas_price: int
    gas_used: int
    input_data: bytes
    nonce: int
    db_id: int = -1
    authorization_list: list[EvmTransactionAuthorization] | None = None

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EvmTransaction):
            return False

        return hash(self) == hash(other)

    def get_or_query_db_id(self, cursor: 'DBCursor') -> int:
        """Returns the DB identifier for the transaction. Assumes it exists in the DB"""
        if self.db_id == -1:
            db_id = cursor.execute(
                'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                (self.tx_hash, self.chain_id.serialize_for_db()),
            ).fetchone()[0]
            object.__setattr__(self, 'db_id', db_id)  # TODO: This will go away at rebase

        return self.db_id

    @property
    def identifier(self) -> str:
        return str(self.chain_id.value) + self.tx_hash.hex()

    def __str__(self) -> str:
        return f'{self.tx_hash.hex()} at {self.chain_id}'


class EvmInternalTransaction(NamedTuple):
    """Represent an internal EVM transaction"""
    parent_tx_hash: EVMTxHash
    chain_id: ChainID
    trace_id: int
    from_address: ChecksumEvmAddress
    to_address: ChecksumEvmAddress | None
    value: int
    gas: int
    gas_used: int

    def serialize(self) -> dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result['tx_hash'] = result['tx_hash'].hex()
        result['chain_id'] = result['chain_id'].serialize()
        result['value'] = str(result['value'])
        result['gas'] = str(result['gas'])
        result['gas_used'] = str(result['gas_used'])
        return result

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EvmInternalTransaction):
            return False

        return hash(self) == hash(other)

    @property
    def identifier(self) -> str:
        return str(self.chain_id.serialize()) + self.parent_tx_hash.hex() + str(self.trace_id)


class ChainType(SerializableEnumNameMixin):
    EVM = auto()
    EVMLIKE = auto()
    SUBSTRATE = auto()
    BITCOIN = auto()
    ETH2 = auto()
    SOLANA = auto()

    def type_to_blockchains(self) -> Sequence['SupportedBlockchain']:
        """Return the set of valid blockchains for the chain type"""
        if self in (ChainType.EVM, ChainType.EVMLIKE):
            return SUPPORTED_EVM_CHAINS + SUPPORTED_EVMLIKE_CHAINS

        if self == ChainType.BITCOIN:
            return SUPPORTED_BITCOIN_CHAINS

        if self == ChainType.SUBSTRATE:
            return get_args(SUPPORTED_SUBSTRATE_CHAINS)

        if self == ChainType.SOLANA:
            return [SupportedBlockchain.SOLANA]

        raise InputError(f'Invalid chain type {self} when removing accounts')


class SupportedBlockchain(SerializableEnumValueMixin):
    """
    These are the currently supported chains in any capacity in rotki
    """
    ETHEREUM = 'ETH'
    ETHEREUM_BEACONCHAIN = 'ETH2'
    BITCOIN = 'BTC'
    BITCOIN_CASH = 'BCH'
    KUSAMA = 'KSM'
    AVALANCHE = 'AVAX'
    POLKADOT = 'DOT'
    OPTIMISM = 'OPTIMISM'
    POLYGON_POS = 'POLYGON_POS'
    ARBITRUM_ONE = 'ARBITRUM_ONE'
    BASE = 'BASE'
    GNOSIS = 'GNOSIS'
    SCROLL = 'SCROLL'
    BINANCE_SC = 'BINANCE_SC'
    ZKSYNC_LITE = 'ZKSYNC_LITE'
    SOLANA = 'SOLANA'

    def __str__(self) -> str:
        return SUPPORTED_BLOCKCHAIN_NAMES_MAPPING.get(self, super().__str__())

    def serialize(self) -> str:
        """
        Serialize is used expose the enum to the frontend. For consistency we expose the key that
        that is used in the backend that is compatible with the default deserialize method.
        """
        return self.get_key()

    def get_key(self) -> str:
        """Returns the key to be used as attribute for this chain in the code"""
        return self.value.lower()

    def is_evm(self) -> bool:
        return self in SUPPORTED_EVM_CHAINS

    def is_evmlike(self) -> bool:
        return self == SupportedBlockchain.ZKSYNC_LITE

    def is_evm_or_evmlike(self) -> bool:
        return self.is_evm() or self.is_evmlike()

    def is_bitcoin(self) -> bool:
        return self in SUPPORTED_BITCOIN_CHAINS

    def is_substrate(self) -> bool:
        return self in get_args(SUPPORTED_SUBSTRATE_CHAINS)

    def get_image_name(self) -> str:
        return SUPPORTED_BLOCKCHAIN_IMAGE_NAME_MAPPING[self]

    def get_native_token_id(self) -> str:
        """Returns the string identifier of the native token for the chain"""
        if self in (SupportedBlockchain.OPTIMISM, SupportedBlockchain.ARBITRUM_ONE, SupportedBlockchain.BASE, SupportedBlockchain.SCROLL, SupportedBlockchain.ZKSYNC_LITE):  # noqa: E501
            return 'ETH'
        if self == SupportedBlockchain.POLYGON_POS:
            return 'eip155:137/erc20:0x0000000000000000000000000000000000001010'
        if self == SupportedBlockchain.GNOSIS:
            return 'XDAI'
        if self == SupportedBlockchain.BINANCE_SC:
            return 'BNB'
        if self == SupportedBlockchain.SOLANA:
            return 'SOL'

        return self.value

    def get_chain_type(self) -> Literal[
        ChainType.EVM,
        ChainType.EVMLIKE,
        ChainType.BITCOIN,
        ChainType.SUBSTRATE,
        ChainType.ETH2,
        ChainType.SOLANA,
    ]:
        """Chain type to return to the API supported chains endpoint"""
        if self.is_evm():
            return ChainType.EVM
        if self.is_evmlike():
            return ChainType.EVMLIKE
        if self.is_substrate():
            return ChainType.SUBSTRATE
        if self.is_bitcoin():
            return ChainType.BITCOIN
        if self == SupportedBlockchain.SOLANA:
            return ChainType.SOLANA
        # else
        return ChainType.ETH2  # the outlier

    def get_address_chain_group(self) -> Literal[
        ChainType.EVMLIKE,
        ChainType.BITCOIN,
        ChainType.SUBSTRATE,
        ChainType.SOLANA,
    ]:
        match (chain_type := self.get_chain_type()):
            case ChainType.EVM | ChainType.EVMLIKE | ChainType.ETH2:
                return ChainType.EVMLIKE
            case _:
                return chain_type

    def ens_coin_type(self) -> int:
        """Return the CoinType number according to EIP-2304, multichain address
        resolution for ENS domains.

        https://eips.ethereum.org/EIPS/eip-2304
        """
        if self == SupportedBlockchain.ETHEREUM:
            return 60
        if self == SupportedBlockchain.BITCOIN:
            return 0
        if self == SupportedBlockchain.BITCOIN_CASH:
            return 145
        if self == SupportedBlockchain.KUSAMA:
            return 434
        if self == SupportedBlockchain.POLKADOT:
            return 354
        if self == SupportedBlockchain.AVALANCHE:
            return 9000
        raise AssertionError(f'Invalid SupportedBlockchain value: {self}')

    @classmethod
    def from_location(cls, location: 'EVM_EVMLIKE_LOCATIONS_TYPE') -> 'SupportedBlockchain':
        """
        Turns a location to a supported chain.
        Caller has to make sure Location is a blockchain, otherwise AttributeError is raised.

        For now since we only got evm/evmlike Locations this works only for them.
        """
        return getattr(cls, location.name)

    def to_chain_id(self) -> SUPPORTED_CHAIN_IDS:
        """Warning: Caller has to make sure this is an evm blockchain"""
        return SUPPORTED_BLOCKCHAIN_TO_CHAINID[self]  # type: ignore

    def to_range_prefix(self, range_type: Literal['txs', 'internaltxs', 'tokentxs']) -> str:
        """Provide the appropriate range prefix for the DB for this chain"""
        return f'{self.value}{range_type}'


"""
Name mapping for chains with more than one word or custom case.
If the name is not specified here, it will use the default value (the chain ID in lowercase).
"""
SUPPORTED_BLOCKCHAIN_NAMES_MAPPING = {
    SupportedBlockchain.ETHEREUM_BEACONCHAIN: 'Ethereum Staking',
    SupportedBlockchain.POLYGON_POS: 'Polygon PoS',
    SupportedBlockchain.ARBITRUM_ONE: 'Arbitrum One',
    SupportedBlockchain.GNOSIS: 'Gnosis',
    SupportedBlockchain.ZKSYNC_LITE: 'ZKSync Lite',
    SupportedBlockchain.BINANCE_SC: 'Binance Smart Chain',
}

SUPPORTED_BLOCKCHAIN_IMAGE_NAME_MAPPING = {
    SupportedBlockchain.ETHEREUM: 'ethereum.svg',
    SupportedBlockchain.ETHEREUM_BEACONCHAIN: 'ethereum.svg',
    SupportedBlockchain.BITCOIN: 'bitcoin.svg',
    SupportedBlockchain.BITCOIN_CASH: 'bitcoin-cash.svg',
    SupportedBlockchain.KUSAMA: 'kusama.svg',
    SupportedBlockchain.AVALANCHE: 'avalanche.svg',
    SupportedBlockchain.POLKADOT: 'polkadot.svg',
    SupportedBlockchain.OPTIMISM: 'optimism.svg',
    SupportedBlockchain.POLYGON_POS: 'polygon_pos.svg',
    SupportedBlockchain.ARBITRUM_ONE: 'arbitrum_one.svg',
    SupportedBlockchain.BASE: 'base.svg',
    SupportedBlockchain.GNOSIS: 'gnosis.svg',
    SupportedBlockchain.SCROLL: 'scroll.svg',
    SupportedBlockchain.ZKSYNC_LITE: 'zksync_lite.svg',
    SupportedBlockchain.BINANCE_SC: 'binance_sc.svg',
    SupportedBlockchain.SOLANA: 'solana.svg',
}

EVM_CHAINS_WITH_TRANSACTIONS_TYPE = Literal[
    SupportedBlockchain.ETHEREUM,
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.POLYGON_POS,
    SupportedBlockchain.ARBITRUM_ONE,
    SupportedBlockchain.BASE,
    SupportedBlockchain.GNOSIS,
    SupportedBlockchain.SCROLL,
    SupportedBlockchain.BINANCE_SC,
]
EVM_CHAINS_WITH_TRANSACTIONS: tuple[EVM_CHAINS_WITH_TRANSACTIONS_TYPE, ...] = typing.get_args(EVM_CHAINS_WITH_TRANSACTIONS_TYPE)  # noqa: E501

EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE = Literal[SupportedBlockchain.ZKSYNC_LITE]
EVMLIKE_CHAINS_WITH_TRANSACTIONS: tuple[EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE, ...] = typing.get_args(EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE)  # noqa: E501

EVM_EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE = EVM_CHAINS_WITH_TRANSACTIONS_TYPE | EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE  # noqa: E501
EVM_EVMLIKE_CHAINS_WITH_TRANSACTIONS: tuple[EVM_EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE, ...] = EVM_CHAINS_WITH_TRANSACTIONS + EVMLIKE_CHAINS_WITH_TRANSACTIONS  # noqa: E501

OTHER_CHAINS_WITH_TRANSACTIONS_TYPE = Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH, SupportedBlockchain.SOLANA]  # noqa: E501
OTHER_CHAINS_WITH_TRANSACTIONS: tuple[OTHER_CHAINS_WITH_TRANSACTIONS_TYPE, ...] = typing.get_args(OTHER_CHAINS_WITH_TRANSACTIONS_TYPE)  # noqa: E501

CHAINS_WITH_TRANSACTIONS_TYPE = EVM_CHAINS_WITH_TRANSACTIONS_TYPE | EVMLIKE_CHAINS_WITH_TRANSACTIONS_TYPE | OTHER_CHAINS_WITH_TRANSACTIONS_TYPE  # noqa: E501
CHAINS_WITH_TRANSACTIONS: tuple[CHAINS_WITH_TRANSACTIONS_TYPE, ...] = EVM_CHAINS_WITH_TRANSACTIONS + EVMLIKE_CHAINS_WITH_TRANSACTIONS + OTHER_CHAINS_WITH_TRANSACTIONS  # noqa: E501

EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE = Literal[
    ChainID.ETHEREUM,
    ChainID.OPTIMISM,
    ChainID.POLYGON_POS,
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.GNOSIS,
    ChainID.SCROLL,
    ChainID.BINANCE_SC,
]

EVM_CHAIN_IDS_WITH_TRANSACTIONS: tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, ...] = typing.get_args(EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE)  # noqa: E501

CHAIN_IDS_WITH_BALANCE_PROTOCOLS = Literal[
    ChainID.ARBITRUM_ONE,
    ChainID.ETHEREUM,
    ChainID.OPTIMISM,
    ChainID.BASE,
    ChainID.POLYGON_POS,
    ChainID.SCROLL,
    ChainID.GNOSIS,
    ChainID.BINANCE_SC,
]

SUPPORTED_EVM_CHAINS_TYPE = Literal[
    SupportedBlockchain.ETHEREUM,
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.AVALANCHE,
    SupportedBlockchain.POLYGON_POS,
    SupportedBlockchain.ARBITRUM_ONE,
    SupportedBlockchain.BASE,
    SupportedBlockchain.GNOSIS,
    SupportedBlockchain.SCROLL,
    SupportedBlockchain.BINANCE_SC,
]
SUPPORTED_EVM_CHAINS: tuple[SUPPORTED_EVM_CHAINS_TYPE, ...] = typing.get_args(SUPPORTED_EVM_CHAINS_TYPE)  # noqa: E501

SUPPORTED_EVMLIKE_CHAINS_TYPE = Literal[SupportedBlockchain.ZKSYNC_LITE]
SUPPORTED_EVMLIKE_CHAINS: tuple[SUPPORTED_EVMLIKE_CHAINS_TYPE, ...] = typing.get_args(SUPPORTED_EVMLIKE_CHAINS_TYPE)  # noqa: E501

SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE = SUPPORTED_EVM_CHAINS_TYPE | SUPPORTED_EVMLIKE_CHAINS_TYPE
SUPPORTED_EVM_EVMLIKE_CHAINS: tuple[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE, ...] = SUPPORTED_EVM_CHAINS + SUPPORTED_EVMLIKE_CHAINS  # noqa: E501

SUPPORTED_NON_BITCOIN_CHAINS = Literal[
    SupportedBlockchain.ETHEREUM,
    SupportedBlockchain.ETHEREUM_BEACONCHAIN,
    SupportedBlockchain.KUSAMA,
    SupportedBlockchain.AVALANCHE,
    SupportedBlockchain.POLKADOT,
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.POLYGON_POS,
    SupportedBlockchain.ARBITRUM_ONE,
    SupportedBlockchain.BASE,
    SupportedBlockchain.GNOSIS,
    SupportedBlockchain.SCROLL,
    SupportedBlockchain.ZKSYNC_LITE,
    SupportedBlockchain.BINANCE_SC,
    SupportedBlockchain.SOLANA,
]

SUPPORTED_BITCOIN_CHAINS_TYPE = Literal[
    SupportedBlockchain.BITCOIN,
    SupportedBlockchain.BITCOIN_CASH,
]
SUPPORTED_BITCOIN_CHAINS: tuple[SUPPORTED_BITCOIN_CHAINS_TYPE, ...] = typing.get_args(SUPPORTED_BITCOIN_CHAINS_TYPE)  # noqa: E501

SUPPORTED_SUBSTRATE_CHAINS = Literal[
    SupportedBlockchain.POLKADOT,
    SupportedBlockchain.KUSAMA,
]

SUPPORTED_BLOCKCHAIN_TO_CHAINID = {
    SupportedBlockchain.ETHEREUM: ChainID.ETHEREUM,
    SupportedBlockchain.OPTIMISM: ChainID.OPTIMISM,
    SupportedBlockchain.AVALANCHE: ChainID.AVALANCHE,
    SupportedBlockchain.POLYGON_POS: ChainID.POLYGON_POS,
    SupportedBlockchain.ARBITRUM_ONE: ChainID.ARBITRUM_ONE,
    SupportedBlockchain.BASE: ChainID.BASE,
    SupportedBlockchain.GNOSIS: ChainID.GNOSIS,
    SupportedBlockchain.SCROLL: ChainID.SCROLL,
    SupportedBlockchain.BINANCE_SC: ChainID.BINANCE_SC,
}
CHAINID_TO_SUPPORTED_BLOCKCHAIN = {
    value: key
    for key, value in SUPPORTED_BLOCKCHAIN_TO_CHAINID.items()
}
NON_EVM_CHAINS = set(SupportedBlockchain) - set(SUPPORTED_BLOCKCHAIN_TO_CHAINID.keys())

EVM_CHAINS_WITH_CHAIN_MANAGER = Literal[
    SupportedBlockchain.ETHEREUM,
    SupportedBlockchain.OPTIMISM,
    SupportedBlockchain.POLYGON_POS,
    SupportedBlockchain.ARBITRUM_ONE,
    SupportedBlockchain.BASE,
    SupportedBlockchain.AVALANCHE,
    SupportedBlockchain.POLKADOT,
    SupportedBlockchain.KUSAMA,
    SupportedBlockchain.GNOSIS,
    SupportedBlockchain.SCROLL,
    SupportedBlockchain.ZKSYNC_LITE,
    SupportedBlockchain.BINANCE_SC,
]

CHAINS_WITH_CHAIN_MANAGER = EVM_CHAINS_WITH_CHAIN_MANAGER | Literal[
    SupportedBlockchain.BITCOIN,
    SupportedBlockchain.BITCOIN_CASH,
]


class Location(DBCharEnumMixIn):
    """Supported Locations"""
    EXTERNAL = 1
    KRAKEN = 2
    POLONIEX = 3
    BITTREX = 4
    BINANCE = 5
    BITMEX = 6
    COINBASE = 7
    TOTAL = 8
    BANKS = 9
    BLOCKCHAIN = 10
    COINBASEPRO = 11
    GEMINI = 12
    EQUITIES = 13
    REALESTATE = 14
    COMMODITIES = 15
    CRYPTOCOM = 16
    UNISWAP = 17
    BITSTAMP = 18
    BINANCEUS = 19
    BITFINEX = 20
    BITCOINDE = 21
    ICONOMI = 22
    KUCOIN = 23
    BALANCER = 24
    LOOPRING = 25
    FTX = 26  # FTX is dead but we keep the location for historical reasons
    NEXO = 27
    BLOCKFI = 28
    INDEPENDENTRESERVE = 29
    GITCOIN = 30
    SUSHISWAP = 31
    SHAPESHIFT = 32
    UPHOLD = 33
    BITPANDA = 34
    BISQ = 35
    FTXUS = 36
    OKX = 37
    ETHEREUM = 38  # on-chain ethereum events
    OPTIMISM = 39  # on-chain optimism events
    POLYGON_POS = 40  # on-chain Polygon POS events
    ARBITRUM_ONE = 41  # on-chain Arbitrum One events
    BASE = 42  # on-chain Base events
    GNOSIS = 43  # on-chain Gnosis events
    WOO = 44
    BYBIT = 45
    SCROLL = 46  # on-chain Scroll events
    ZKSYNC_LITE = 47
    HTX = 48
    BITCOIN = 49
    BITCOIN_CASH = 50
    POLKADOT = 51
    KUSAMA = 52
    COINBASEPRIME = 53
    BINANCE_SC = 54  # on-chain Binance Smart Chain events
    SOLANA = 55

    @staticmethod
    def from_chain_id(chain_id: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE) -> 'EVM_LOCATIONS_TYPE':
        if chain_id == ChainID.ETHEREUM:
            return Location.ETHEREUM

        if chain_id == ChainID.OPTIMISM:
            return Location.OPTIMISM

        if chain_id == ChainID.ARBITRUM_ONE:
            return Location.ARBITRUM_ONE

        if chain_id == ChainID.BASE:
            return Location.BASE

        if chain_id == ChainID.GNOSIS:
            return Location.GNOSIS

        if chain_id == ChainID.SCROLL:
            return Location.SCROLL

        if chain_id == ChainID.BINANCE_SC:
            return Location.BINANCE_SC

        # else
        return Location.POLYGON_POS

    def to_chain_id(self) -> int:
        """EVMLocation to chain id

        Dealing directly with ints since it's used as integers mostly and helps with import hell
        """
        assert self in EVM_LOCATIONS
        if self == Location.ETHEREUM:
            return ChainID.ETHEREUM.value
        if self == Location.OPTIMISM:
            return ChainID.OPTIMISM.value
        if self == Location.ARBITRUM_ONE:
            return ChainID.ARBITRUM_ONE.value
        if self == Location.BASE:
            return ChainID.BASE.value
        if self == Location.GNOSIS:
            return ChainID.GNOSIS.value
        if self == Location.SCROLL:
            return ChainID.SCROLL.value
        if self == Location.BINANCE_SC:
            return ChainID.BINANCE_SC.value
        assert self == Location.POLYGON_POS, 'should have only been polygon pos here'
        return ChainID.POLYGON_POS.value

    @staticmethod
    def from_chain(chain: CHAINS_WITH_TRANSACTIONS_TYPE) -> 'BLOCKCHAIN_LOCATIONS_TYPE':
        assert chain in CHAINS_WITH_TRANSACTIONS
        match chain:
            case SupportedBlockchain.ETHEREUM:
                return Location.ETHEREUM
            case SupportedBlockchain.OPTIMISM:
                return Location.OPTIMISM
            case SupportedBlockchain.POLYGON_POS:
                return Location.POLYGON_POS
            case SupportedBlockchain.ARBITRUM_ONE:
                return Location.ARBITRUM_ONE
            case SupportedBlockchain.BASE:
                return Location.BASE
            case SupportedBlockchain.GNOSIS:
                return Location.GNOSIS
            case SupportedBlockchain.SCROLL:
                return Location.SCROLL
            case SupportedBlockchain.BINANCE_SC:
                return Location.BINANCE_SC
            case SupportedBlockchain.ZKSYNC_LITE:
                return Location.ZKSYNC_LITE
            case SupportedBlockchain.BITCOIN:
                return Location.BITCOIN
            case SupportedBlockchain.BITCOIN_CASH:
                return Location.BITCOIN_CASH
            case SupportedBlockchain.SOLANA:
                return Location.SOLANA
            case _:  # should never happen
                raise AssertionError(f'Got in Location.from_chain for {chain}')

    def is_evm(self) -> bool:
        return self in EVM_LOCATIONS

    def is_evmlike(self) -> bool:
        return self in EVMLIKE_LOCATIONS

    def is_evm_or_evmlike(self) -> bool:
        return self in EVM_EVMLIKE_LOCATIONS

    def is_bitcoin(self) -> bool:
        return self in BITCOIN_LOCATIONS


EVM_LOCATIONS_TYPE = Literal[Location.ETHEREUM, Location.OPTIMISM, Location.POLYGON_POS, Location.ARBITRUM_ONE, Location.BASE, Location.GNOSIS, Location.SCROLL, Location.BINANCE_SC]  # noqa: E501
EVM_LOCATIONS: tuple[EVM_LOCATIONS_TYPE, ...] = typing.get_args(EVM_LOCATIONS_TYPE)
EVMLIKE_LOCATIONS_TYPE = Literal[Location.ZKSYNC_LITE]
EVMLIKE_LOCATIONS: tuple[EVMLIKE_LOCATIONS_TYPE, ...] = typing.get_args(EVMLIKE_LOCATIONS_TYPE)
EVM_EVMLIKE_LOCATIONS_TYPE = EVM_LOCATIONS_TYPE | EVMLIKE_LOCATIONS_TYPE
EVM_EVMLIKE_LOCATIONS: tuple[EVM_EVMLIKE_LOCATIONS_TYPE, ...] = EVM_LOCATIONS + EVMLIKE_LOCATIONS
BITCOIN_LOCATIONS_TYPE = Literal[Location.BITCOIN, Location.BITCOIN_CASH]
BITCOIN_LOCATIONS: tuple[BITCOIN_LOCATIONS_TYPE, ...] = typing.get_args(BITCOIN_LOCATIONS_TYPE)
BLOCKCHAIN_LOCATIONS_TYPE: TypeAlias = EVM_EVMLIKE_LOCATIONS_TYPE | BITCOIN_LOCATIONS_TYPE | Literal[Location.SOLANA]  # noqa: E501
BLOCKCHAIN_LOCATIONS: tuple[BLOCKCHAIN_LOCATIONS_TYPE, ...] = EVM_EVMLIKE_LOCATIONS + BITCOIN_LOCATIONS + (Location.SOLANA,)  # noqa: E501


class ExchangeAuthCredentials(NamedTuple):
    """
    Data structure that is used for editing credentials of exchanges.
    If a certain field is not None, it is modified in the exchange, otherwise
    the current value is kept.
    """
    api_key: ApiKey | None
    api_secret: ApiSecret | None
    passphrase: str | None


class ExchangeApiCredentials(NamedTuple):
    """Represents Credentials for Exchanges

    The Api in question must at least have an API key.
    """
    name: str  # A unique name to identify this particular Location credentials
    location: Location
    api_key: ApiKey
    api_secret: ApiSecret | None
    passphrase: str | None = None


EXTERNAL_EXCHANGES = (
    Location.CRYPTOCOM,
    Location.BLOCKFI,
    Location.NEXO,
    Location.SHAPESHIFT,
    Location.UPHOLD,
    Location.BISQ,
    Location.BITMEX,
)


class ExchangeLocationID(NamedTuple):
    name: str
    location: Location

    def serialize(self) -> dict:
        return {'name': self.name, 'location': self.location.serialize()}

    @classmethod
    def deserialize(
            cls: type['ExchangeLocationID'],
            data: dict['str', Any],
    ) -> 'ExchangeLocationID':
        """May raise DeserializationError"""
        try:
            return cls(
                name=data['name'],
                location=Location.deserialize(data['location']),
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e


class EnsMapping(NamedTuple):
    address: ChecksumEvmAddress
    name: str
    last_update: Timestamp = Timestamp(0)


class CostBasisMethod(SerializableEnumNameMixin):
    FIFO = auto()
    LIFO = auto()
    HIFO = auto()
    ACB = auto()


ADDRESSBOOK_BLOCKCHAIN_GROUP_PREFIX: Final = 'TYPE_'  # prefix used along the address chain type to mark in the DB that the address entry is valid for any blockchain  # noqa: E501


class AddressbookEntry(NamedTuple):
    address: 'BlockchainAddress'
    name: str
    blockchain: SupportedBlockchain | None

    def serialize(self) -> dict[str, str | None]:
        return {
            'address': self.address,
            'name': self.name,
            'blockchain': self.blockchain.serialize() if self.blockchain is not None else None,
        }

    @staticmethod
    def check_chain_ecosystem(address: 'BlockchainAddress') -> Literal[
        ChainType.BITCOIN,
        ChainType.EVMLIKE,
        ChainType.SUBSTRATE,
        ChainType.SOLANA,
    ]:
        """Get the chain ecosystem for the provided address.

        May raise:
            - AddressNotSupported
        """
        with suppress(ValueError):
            to_checksum_address(address)
            return ChainType.EVMLIKE

        if is_valid_btc_address(address) or is_valid_bitcoin_cash_address(address):
            return ChainType.BITCOIN
        elif (
            is_valid_ss58_address(value=address, valid_ss58_format=0) or  # Polkadot
            is_valid_ss58_address(value=address, valid_ss58_format=2)     # Kusama
        ):
            return ChainType.SUBSTRATE
        if is_valid_solana_address(address=address):
            return ChainType.SOLANA

        # Whenever we add a new ecosystem we need to update this function.
        raise AddressNotSupported(f'Unsupported address {address}')

    @staticmethod
    def get_ecosystem_key_by_address(address: 'BlockchainAddress') -> str:
        """May raise:
            - AddressNotSupported
        """
        ecosystem = AddressbookEntry.check_chain_ecosystem(address)
        return f'{ADDRESSBOOK_BLOCKCHAIN_GROUP_PREFIX}{ecosystem.name}'

    def get_ecosystem_key(self) -> str:
        """May raise:
            - AddressNotSupported
        """
        return self.get_ecosystem_key_by_address(self.address)

    def serialize_for_db(self) -> tuple[str, str, str]:
        return (
            self.address,
            self.name,
            self.blockchain.value if self.blockchain is not None else self.get_ecosystem_key(),
        )

    @classmethod
    def deserialize(cls: type['AddressbookEntry'], data: dict[str, Any]) -> 'AddressbookEntry':
        """May raise:
        -KeyError if required keys are missing
        """
        return cls(
            address=data['address'],
            name=data['name'],
            blockchain=SupportedBlockchain.deserialize(data['blockchain']) if data['blockchain'] is not None else None,  # noqa: E501
        )


class AddressbookEntryWithSource(NamedTuple):
    """AddressbookEntry with source information - used for /names/all endpoint"""
    address: BlockchainAddress
    name: str
    blockchain: SupportedBlockchain | None
    source: 'AddressNameSource'

    def serialize(self) -> dict[str, str | None]:
        return {
            'address': self.address,
            'name': self.name,
            'blockchain': self.blockchain.serialize() if self.blockchain is not None else None,
            'source': self.source,
        }

    def serialize_for_db(self) -> tuple[str, str, str]:
        return (
            self.address,
            self.name,
            (
                self.blockchain.value
                if self.blockchain is not None
                else AddressbookEntry.get_ecosystem_key_by_address(self.address)
            ),
        )

    @classmethod
    def deserialize(
            cls: type['AddressbookEntryWithSource'],
            data: dict[str, Any],
    ) -> 'AddressbookEntryWithSource':
        """May raise:
        -KeyError if required keys are missing
        """
        return cls(
            address=data['address'],
            name=data['name'],
            blockchain=SupportedBlockchain.deserialize(data['blockchain']) if data['blockchain'] is not None else None,  # noqa: E501
            source=data['source'],
        )

    def __str__(self) -> str:
        return f'Addressbook entry with name "{self.name}", address "{self.address}" and blockchain {str(self.blockchain) if self.blockchain is not None else None}'  # noqa: E501


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class LocationAssetMappingDeleteEntry:
    location: 'Location | None'
    location_symbol: str

    @classmethod
    def deserialize(cls: type['LocationAssetMappingDeleteEntry'], data: dict[str, Any]) -> 'LocationAssetMappingDeleteEntry':  # noqa: E501
        """May raise:
        -DeserializationError if required keys are missing
        """
        try:
            return cls(
                location=data['location'],
                location_symbol=data['location_symbol'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    def serialize_for_db(self) -> tuple[Any, ...]:
        return self.location_symbol, None if self.location is None else self.location.serialize_for_db()  # noqa: E501

    def __str__(self) -> str:
        return f'{self.location_symbol} in {self.location}'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class LocationAssetMappingUpdateEntry(LocationAssetMappingDeleteEntry):
    asset: 'Asset'

    @classmethod
    def deserialize(cls: type['LocationAssetMappingUpdateEntry'], data: dict[str, Any]) -> 'LocationAssetMappingUpdateEntry':  # noqa: E501
        """May raise:
        -DeserializationError if required keys are missing
        """
        try:
            return cls(
                asset=data['asset'],
                location=data['location'],
                location_symbol=data['location_symbol'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    def serialize_for_db(self) -> tuple[Any, ...]:
        return self.asset.serialize(), *super().serialize_for_db()


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class CounterpartyAssetMappingDeleteEntry:
    """A counterparty asset mapping delete entry"""
    counterparty: str
    counterparty_symbol: str

    @classmethod
    def deserialize(cls: type['CounterpartyAssetMappingDeleteEntry'], data: dict[str, Any]) -> 'CounterpartyAssetMappingDeleteEntry':  # noqa: E501
        try:
            return cls(
                counterparty=data['counterparty'],
                counterparty_symbol=data['counterparty_symbol'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    def serialize_for_db(self) -> tuple[str, ...]:
        return self.counterparty_symbol, self.counterparty

    def __str__(self) -> str:
        return f'{self.counterparty_symbol} in {self.counterparty}'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class CounterpartyAssetMappingUpdateEntry(CounterpartyAssetMappingDeleteEntry):
    """A counterparty asset mapping update entry"""
    asset: 'Asset'

    @classmethod
    def deserialize(cls: type['CounterpartyAssetMappingUpdateEntry'], data: dict[str, Any]) -> 'CounterpartyAssetMappingUpdateEntry':  # noqa: E501
        try:
            return cls(
                asset=data['asset'],
                counterparty=data['counterparty'],
                counterparty_symbol=data['counterparty_symbol'],
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    def serialize_for_db(self) -> tuple[str, ...]:
        return self.asset.serialize(), *super().serialize_for_db()


T = TypeVar('T')


class GenericOptionalChainAddress(NamedTuple, Generic[T]):
    address: T
    blockchain: SupportedBlockchain | None


class OptionalChainAddress(GenericOptionalChainAddress[ChecksumAddress]):
    ...


class OptionalBlockchainAddress(GenericOptionalChainAddress[BlockchainAddress]):
    ...


class ChainAddress(OptionalChainAddress):
    blockchain: SupportedBlockchain


class AddressbookType(SerializableEnumNameMixin):
    GLOBAL = 1
    PRIVATE = 2


class UserNote(NamedTuple):
    identifier: int
    title: str
    content: str
    location: str
    last_update_timestamp: Timestamp
    is_pinned: bool

    def serialize(self) -> dict[str, str | int]:
        """Serialize a `UserNote` object into a dict."""
        return {
            'identifier': self.identifier,
            'title': self.title,
            'content': self.content,
            'location': self.location,
            'last_update_timestamp': self.last_update_timestamp,
            'is_pinned': self.is_pinned,
        }

    @classmethod
    def deserialize(cls, entry: dict[str, Any]) -> 'UserNote':
        """Turns a dict into a `UserNote` object.
        May raise:
        - DeserializationError if required keys are missing.
        """
        try:
            return cls(
                identifier=entry['identifier'],
                title=entry['title'],
                content=entry['content'],
                location=entry['location'],
                last_update_timestamp=entry['last_update_timestamp'],
                is_pinned=entry['is_pinned'],
            )
        except KeyError as e:
            raise DeserializationError(f'Failed to deserialize dict due to missing key: {e!s}') from e  # noqa: E501

    @classmethod
    def deserialize_from_db(cls, entry: tuple[int, str, str, str, int, int]) -> 'UserNote':
        """Turns a `user_note` db entry into a `UserNote` object."""
        return cls(
            identifier=entry[0],
            title=entry[1],
            content=entry[2],
            location=entry[3],
            last_update_timestamp=Timestamp(entry[4]),
            is_pinned=bool(entry[5]),
        )


class FValWithTolerance(NamedTuple):
    """Represents a value with a tolerance around it.
    Especially useful for comparing values with lots of decimal places"""
    value: FVal
    tolerance: FVal = ZERO


class TokenKind(DBCharEnumMixIn):
    ERC20 = auto()
    ERC721 = auto()
    UNKNOWN = auto()

    # Solana tokens
    SPL_TOKEN = auto()  # fungible tokens on solana - https://spl.solana.com/token
    SPL_NFT = auto()  # nfts on solana - https://developers.metaplex.com/token-metadata

    @classmethod
    def deserialize_evm_from_db(cls, value: Any) -> 'EVM_TOKEN_KINDS_TYPE':
        """Deserialize specifically for EVM token kinds"""
        if (result := cls.deserialize_from_db(value)) not in (TokenKind.ERC20, TokenKind.ERC721):
            raise DeserializationError(f'Expected EVM token kind, got {result}')

        return result  # type: ignore[return-value]  # the check above ensures it's an evm token kind.

    @classmethod
    def deserialize_solana_from_db(cls, value: Any) -> 'SOLANA_TOKEN_KINDS_TYPE':
        """Deserialize specifically for Solana token kinds"""
        if (result := cls.deserialize_from_db(value)) not in (TokenKind.SPL_TOKEN, TokenKind.SPL_NFT):  # noqa: E501
            raise DeserializationError(f'Expected solana token kind, got {result}')

        return result  # type: ignore[return-value]  # the check above ensures it's solana token kind.


EVM_TOKEN_KINDS_TYPE = Literal[TokenKind.ERC20, TokenKind.ERC721]
EVM_TOKEN_KINDS: tuple[EVM_TOKEN_KINDS_TYPE, ...] = typing.get_args(EVM_TOKEN_KINDS_TYPE)
SOLANA_TOKEN_KINDS_TYPE = Literal[TokenKind.SPL_TOKEN, TokenKind.SPL_NFT]
SOLANA_TOKEN_KINDS: tuple[SOLANA_TOKEN_KINDS_TYPE, ...] = typing.get_args(SOLANA_TOKEN_KINDS_TYPE)


class CacheType(Enum):
    """It contains all types both for the general cache table and the unique cache table
    Important: When adding a new cache for a protocol that the user should be able to refresh
    please add it to `ProtocolsWithCache`.
    """
    CURVE_LP_TOKENS = auto()
    CURVE_POOL_ADDRESS = auto()  # get pool addr by lp token
    CURVE_POOL_TOKENS = auto()  # get pool tokens by pool addr
    YEARN_VAULTS = auto()  # get yearn vaults information
    MAKERDAO_VAULT_ILK = auto()  # ilk(collateral type) to info (underlying_asset, join address)
    CURVE_GAUGE_ADDRESS = auto()  # get gauge address by pool address
    VELODROME_POOL_ADDRESS = auto()  # get pool address information
    VELODROME_GAUGE_ADDRESS = auto()  # get gauge address by pool address
    AERODROME_POOL_ADDRESS = auto()  # get pool address information
    AERODROME_GAUGE_ADDRESS = auto()  # get gauge address by pool address
    ENS_NAMEHASH = auto()  # map ENS namehash -> ens name
    ENS_LABELHASH = auto()  # map ENS labelhash -> ens name
    CONVEX_POOL_ADDRESS = auto()  # get convex pool addr
    CONVEX_POOL_NAME = auto()  # map convex pool rewards address -> pool name
    SPAM_ASSET_FALSE_POSITIVE = auto()  # assets that shouldn't be marked as spam automatically
    COINLIST = auto()  # coinlist / all coins cache for various oracles
    AIRDROPS_METADATA = auto()  # airdrops index fetched from rotki/data repo
    AIRDROPS_HASH = auto()  # hash of airdrops csv file
    GEARBOX_POOL_ADDRESS = auto()
    GEARBOX_POOL_NAME = auto()
    GEARBOX_POOL_FARMING_TOKEN = auto()
    GEARBOX_POOL_LP_TOKENS = auto()
    HOP_POOL_ADDRESS = auto()
    EXTRAFI_LENDING_RESERVES = auto()  # maps reserve id + blockchain to the underlying token
    EXTRAFI_FARM_METADADATA = auto()
    EXTRAFI_REWARD_CONTRACTS = auto()
    EXTRAFI_NEXT_RESERVE_ID = auto()
    EFP_SLOT_ADDRESS = auto()
    MORPHO_VAULTS = auto()
    MORPHO_REWARD_DISTRIBUTORS = auto()
    BALANCER_V1_POOLS = auto()
    BALANCER_V2_POOLS = auto()
    BALANCER_V3_POOLS = auto()
    CURVE_LENDING_VAULTS = auto()
    CURVE_LENDING_VAULT_CONTROLLER = auto()
    CURVE_LENDING_VAULT_BORROWED_TOKEN = auto()
    AURA_POOLS = auto()  # stores count of pools in db + chain_id (stringified)
    BALANCER_V1_GAUGES = auto()  # stores gauges + chain_id
    BALANCER_V2_GAUGES = auto()  # stores gauges + chain_id
    BALANCER_V3_GAUGES = auto()  # stores gauges + chain_id
    VELODROME_GAUGE_FEE_ADDRESS = auto()
    VELODROME_GAUGE_BRIBE_ADDRESS = auto()
    AERODROME_GAUGE_FEE_ADDRESS = auto()
    AERODROME_GAUGE_BRIBE_ADDRESS = auto()
    CURVE_LENDING_VAULT_GAUGE = auto()
    CURVE_CRVUSD_CONTROLLERS = auto()
    CURVE_CRVUSD_COLLATERAL_TOKEN = auto()
    CURVE_CRVUSD_AMM = auto()
    STAKEDAO_GAUGES = auto()
    PENDLE_POOLS = auto()
    PENDLE_SY_TOKENS = auto()
    PENDLE_YIELD_TOKENS = auto()  # store the count of all SYs, PTs, YTs & LP tokens per chain
    BEEFY_VAULTS = auto()
    MERKL_REWARD_PROTOCOLS = auto()

    def serialize(self) -> str:
        # Using custom serialize method instead of SerializableEnumMixin since mixin replaces
        # `_` with ` ` and we don't need spaces here
        # TODO: Shorten all cache types not only velodrome
        if self.name.startswith(('VELODROME', 'AERODROME')):
            parts = self.name.split('_')
            return parts[0][:4] + ''.join(p[0] for p in parts[1:-1])  # Shorten the name that is stored in the db to save space. For example: VELODROME_POOL_ADDRESS -> VELOP  # noqa: E501

        return self.name


class ProtocolsWithCache(SerializableEnumNameMixin):
    """"Enumeration of all the protocols that have cache keys that can be
    refreshed by the user manually. It doesn't match the counterparties
    because some protocols have different versions.
    """
    CURVE = auto()
    VELODROME = auto()
    AERODROME = auto()
    YEARN = auto()
    MAKER = auto()
    AAVE = auto()
    CONVEX = auto()
    GEARBOX = auto()
    SPARK = auto()
    BALANCER_V1 = auto()
    BALANCER_V2 = auto()
    BALANCER_V3 = auto()
    MERKL = auto()
    BEEFY_FINANCE = auto()
    # TODO: ETH_WITHDRAWALS and ETH_BLOCKS should be removed
    #  once https://github.com/rotki/rotki/issues/9302 is implemented
    ETH_WITHDRAWALS = auto()
    ETH_BLOCKS = auto()


UniqueCacheType = Literal[
    CacheType.CURVE_POOL_ADDRESS,
    CacheType.MAKERDAO_VAULT_ILK,
    CacheType.CURVE_GAUGE_ADDRESS,
    CacheType.YEARN_VAULTS,
    CacheType.ENS_NAMEHASH,
    CacheType.ENS_LABELHASH,
    CacheType.CONVEX_POOL_NAME,
    CacheType.COINLIST,
    CacheType.AIRDROPS_METADATA,
    CacheType.AIRDROPS_HASH,
    CacheType.GEARBOX_POOL_ADDRESS,
    CacheType.GEARBOX_POOL_NAME,
    CacheType.GEARBOX_POOL_FARMING_TOKEN,
    CacheType.HOP_POOL_ADDRESS,
    CacheType.EXTRAFI_LENDING_RESERVES,
    CacheType.EXTRAFI_FARM_METADADATA,
    CacheType.EXTRAFI_NEXT_RESERVE_ID,
    CacheType.EFP_SLOT_ADDRESS,
    CacheType.MORPHO_VAULTS,
    CacheType.CURVE_LENDING_VAULTS,
    CacheType.CURVE_LENDING_VAULT_CONTROLLER,
    CacheType.CURVE_LENDING_VAULT_BORROWED_TOKEN,
    CacheType.AURA_POOLS,
    CacheType.CURVE_LENDING_VAULT_GAUGE,
    CacheType.CURVE_CRVUSD_COLLATERAL_TOKEN,
    CacheType.CURVE_CRVUSD_AMM,
    CacheType.PENDLE_YIELD_TOKENS,
    CacheType.BEEFY_VAULTS,
    CacheType.MERKL_REWARD_PROTOCOLS,
]

UNIQUE_CACHE_KEYS: tuple[UniqueCacheType, ...] = typing.get_args(UniqueCacheType)

GeneralCacheType = Literal[
    CacheType.CURVE_LP_TOKENS,
    CacheType.CURVE_POOL_TOKENS,
    CacheType.VELODROME_POOL_ADDRESS,
    CacheType.VELODROME_GAUGE_ADDRESS,
    CacheType.VELODROME_GAUGE_BRIBE_ADDRESS,
    CacheType.VELODROME_GAUGE_FEE_ADDRESS,
    CacheType.AERODROME_POOL_ADDRESS,
    CacheType.AERODROME_GAUGE_ADDRESS,
    CacheType.AERODROME_GAUGE_BRIBE_ADDRESS,
    CacheType.AERODROME_GAUGE_FEE_ADDRESS,
    CacheType.CONVEX_POOL_ADDRESS,
    CacheType.SPAM_ASSET_FALSE_POSITIVE,
    CacheType.GEARBOX_POOL_ADDRESS,
    CacheType.GEARBOX_POOL_LP_TOKENS,
    CacheType.EXTRAFI_REWARD_CONTRACTS,
    CacheType.BALANCER_V1_POOLS,
    CacheType.BALANCER_V2_POOLS,
    CacheType.BALANCER_V3_POOLS,
    CacheType.BALANCER_V1_GAUGES,
    CacheType.BALANCER_V2_GAUGES,
    CacheType.BALANCER_V3_GAUGES,
    CacheType.MORPHO_REWARD_DISTRIBUTORS,
    CacheType.CURVE_CRVUSD_CONTROLLERS,
    CacheType.STAKEDAO_GAUGES,
    CacheType.PENDLE_POOLS,
    CacheType.PENDLE_SY_TOKENS,
]


class OracleSource(SerializableEnumNameMixin):
    """
    Abstraction to represent a variable that could be either HistoricalPriceOracle
    or CurrentPriceOracle. Can't have any member since you can't override them later
    """


AddressNameSource = Literal[
    'blockchain_account',
    'ens_names',
    'ethereum_tokens',
    'global_addressbook',
    'hardcoded_mappings',
    'private_addressbook',
]

DEFAULT_ADDRESS_NAME_PRIORITY: Sequence[AddressNameSource] = (
    'private_addressbook',
    'blockchain_account',
    'global_addressbook',
    'ethereum_tokens',
    'hardcoded_mappings',
    'ens_names',
)


class HistoryEventQueryType(SerializableEnumNameMixin):
    """Locations to query for history event data"""
    ETH_WITHDRAWALS = auto()
    BLOCK_PRODUCTIONS = auto()
    MONERIUM = auto()
    GNOSIS_PAY = auto()
