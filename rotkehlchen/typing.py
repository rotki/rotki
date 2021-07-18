from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, NewType, Optional, Tuple, Union

from eth_typing import ChecksumAddress
from typing_extensions import Literal

from rotkehlchen.chain.substrate.typing import KusamaAddress
from rotkehlchen.fval import FVal
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn  # lgtm[py/unsafe-cyclic-import]

ModuleName = Literal[
    'makerdao_dsr',
    'makerdao_vaults',
    'aave',
    'compound',
    'yearn_vaults',
    'yearn_vaults_v2',
    'uniswap',
    'adex',
    'loopring',
    'balancer',
    'eth2',
]

# TODO: Turn this into some kind of light data structure and not just a mapping
# This is a mapping of module ids to human readable names
AVAILABLE_MODULES_MAP = {
    'makerdao_dsr': 'MakerDAO DSR',
    'makerdao_vaults': 'MakerDAO Vaults',
    'aave': 'Aave',
    'compound': 'Compound',
    'yearn_vaults': 'Yearn Vaults',
    'yearn_vaults_v2': 'Yearn V2 Vaults',
    'uniswap': 'Uniswap',
    'adex': 'AdEx',
    'loopring': 'Loopring',
    'balancer': 'Balancer',
    'eth2': 'Eth2',
}


IMPORTABLE_LOCATIONS = Literal[
    'cointracking.info',
    'cryptocom',
    'blockfi-transactions',
    'blockfi-trades',
    'nexo',
    'gitcoin',
]

UNISWAP_PROTOCOL = 'UNI-V2'
YEARN_VAULTS_V2_PROTOCOL = 'yearn_vaults_v2'
CURVE_POOL_PROTOCOL = 'curve_pool'


KnownProtocolsAssets = (
    UNISWAP_PROTOCOL,
    YEARN_VAULTS_V2_PROTOCOL,
    CURVE_POOL_PROTOCOL,
)


T_Timestamp = int
Timestamp = NewType('Timestamp', T_Timestamp)

T_TimestampMS = int
TimestampMS = NewType('TimestampMS', T_TimestampMS)

T_ApiKey = str
ApiKey = NewType('ApiKey', T_ApiKey)

T_ApiSecret = bytes
ApiSecret = NewType('ApiSecret', T_ApiSecret)

T_B64EncodedBytes = bytes
B64EncodedBytes = NewType('B64EncodedBytes', T_B64EncodedBytes)

T_B64EncodedString = str
B64EncodedString = NewType('B64EncodedString', T_B64EncodedString)

T_HexColorCode = str
HexColorCode = NewType('HexColorCode', T_HexColorCode)


class ExternalService(Enum):
    ETHERSCAN = 0
    CRYPTOCOMPARE = 1
    BEACONCHAIN = 2
    LOOPRING = 3

    @staticmethod
    def serialize(name: str) -> Optional['ExternalService']:
        if name == 'etherscan':
            return ExternalService.ETHERSCAN
        if name == 'cryptocompare':
            return ExternalService.CRYPTOCOMPARE
        if name == 'beaconchain':
            return ExternalService.BEACONCHAIN
        if name == 'loopring':
            return ExternalService.LOOPRING
        # else
        return None


class ExternalServiceApiCredentials(NamedTuple):
    """Represents Credentials for various External APIs. Etherscan, Cryptocompare e.t.c.

    The Api in question must at least have an API key.
    """
    service: ExternalService
    api_key: ApiKey

    def serialize_for_db(self) -> Tuple[str, str]:
        return (self.service.name.lower(), self.api_key)


T_TradePair = str
TradePair = NewType('TradePair', T_TradePair)

T_EthAddres = str
EthAddress = NewType('EthAddress', T_EthAddres)

ChecksumEthAddress = ChecksumAddress

T_BTCAddress = str
BTCAddress = NewType('BTCAddress', T_BTCAddress)

BlockchainAddress = Union[
    EthAddress,
    BTCAddress,
    ChecksumEthAddress,
    KusamaAddress,
    str,
]
ListOfBlockchainAddresses = Union[
    List[BTCAddress],
    List[ChecksumEthAddress],
    List[KusamaAddress],
]


T_EmptyStr = str
EmptyStr = NewType('EmptyStr', T_EmptyStr)

T_Fee = FVal
Fee = NewType('Fee', T_Fee)

T_Price = FVal
Price = NewType('Price', T_Price)

T_AssetAmount = FVal
AssetAmount = NewType('AssetAmount', T_AssetAmount)

T_TradeID = str
TradeID = NewType('TradeID', T_TradeID)


T_EventType = str
EventType = NewType('EventType', T_EventType)


class EthereumTransaction(NamedTuple):
    """Represent an Ethereum transaction"""
    tx_hash: bytes
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEthAddress
    to_address: Optional[ChecksumEthAddress]
    value: int
    gas: int
    gas_price: int
    gas_used: int
    input_data: bytes
    # The ethereum transaction nonce. Even though for normal ethereum transactions
    # this can't be negative it can be for us. IF it's negative it means that
    # this is an internal transaction returned by etherscan.
    nonce: int

    def serialize(self) -> Dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result['tx_hash'] = '0x' + result['tx_hash'].hex()
        result['input_data'] = '0x' + result['input_data'].hex()

        # Most integers are turned to string to be sent via the API
        result['value'] = str(result['value'])
        result['gas'] = str(result['gas'])
        result['gas_price'] = str(result['gas_price'])
        result['gas_used'] = str(result['gas_used'])
        return result

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if not isinstance(other, EthereumTransaction):
            return False

        return hash(self) == hash(other)

    @property
    def identifier(self) -> str:
        return '0x' + self.tx_hash.hex() + self.from_address + str(self.nonce)


class SupportedBlockchain(Enum):
    """These are the blockchains for which account tracking is supported """
    ETHEREUM = 'ETH'
    BITCOIN = 'BTC'
    KUSAMA = 'KSM'

    def get_address_type(self) -> Callable:
        if self == SupportedBlockchain.ETHEREUM:
            return ChecksumEthAddress
        if self == SupportedBlockchain.BITCOIN:
            return BTCAddress
        if self == SupportedBlockchain.KUSAMA:
            return KusamaAddress
        raise AssertionError(f'Invalid SupportedBlockchain value: {self}')

    def ens_coin_type(self) -> int:
        """Return the CoinType number according to EIP-2304, multichain address
        resolution for ENS domains.

        https://eips.ethereum.org/EIPS/eip-2304
        """
        if self == SupportedBlockchain.ETHEREUM:
            return 60
        if self == SupportedBlockchain.BITCOIN:
            return 0
        if self == SupportedBlockchain.KUSAMA:
            return 434
        raise AssertionError(f'Invalid SupportedBlockchain value: {self}')


class TradeType(Enum):
    BUY = 1
    SELL = 2
    SETTLEMENT_BUY = 3
    SETTLEMENT_SELL = 4

    def __str__(self) -> str:
        if self == TradeType.BUY:
            return 'buy'
        if self == TradeType.SELL:
            return 'sell'
        if self == TradeType.SETTLEMENT_BUY:
            return 'settlement_buy'
        if self == TradeType.SETTLEMENT_SELL:
            return 'settlement_sell'
        # else
        raise RuntimeError(f'Corrupt value {self} for TradeType -- Should never happen')

    def serialize_for_db(self) -> str:
        if self == TradeType.BUY:
            return 'A'
        if self == TradeType.SELL:
            return 'B'
        if self == TradeType.SETTLEMENT_BUY:
            return 'C'
        if self == TradeType.SETTLEMENT_SELL:
            return 'D'
        # else
        raise RuntimeError(f'Corrupt value {self} for TradeType -- Should never happen')


class Location(DBEnumMixIn):
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
    FTX = 26
    NEXO = 27
    BLOCKFI = 28
    INDEPENDENTRESERVE = 29
    GITCOIN = 30


class AssetMovementCategory(Enum):
    """Supported Asset Movement Types so far only deposit and withdrawals"""
    DEPOSIT = 1
    WITHDRAWAL = 2

    def __str__(self) -> str:
        if self == AssetMovementCategory.DEPOSIT:
            return 'deposit'
        if self == AssetMovementCategory.WITHDRAWAL:
            return 'withdrawal'
        # else
        raise RuntimeError(
            f'Corrupt value {self} for AssetMovementCategory -- Should never happen',
        )

    def serialize_for_db(self) -> str:
        if self == AssetMovementCategory.DEPOSIT:
            return 'A'
        if self == AssetMovementCategory.WITHDRAWAL:
            return 'B'
        # else
        raise RuntimeError(
            f'Corrupt value {self} for AssetMovementCategory -- Should never happen',
        )


class BlockchainAccountData(NamedTuple):
    address: BlockchainAddress
    label: Optional[str] = None
    tags: Optional[List[str]] = None


class ExchangeApiCredentials(NamedTuple):
    """Represents Credentials for Exchanges

    The Api in question must at least have an API key and an API secret.
    """
    name: str  # A unique name to identify this particular Location credentials
    location: Location
    api_key: ApiKey
    api_secret: ApiSecret
    passphrase: Optional[str] = None


EXTERNAL_EXCHANGES: List = [Location.CRYPTOCOM, Location.BLOCKFI, Location.NEXO]
EXTERNAL_LOCATION = [Location.EXTERNAL] + EXTERNAL_EXCHANGES
