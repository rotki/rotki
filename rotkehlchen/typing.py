
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, NewType, Optional, Tuple, Union

from eth_utils.typing import ChecksumAddress
from typing_extensions import Literal

from rotkehlchen.fval import FVal

ModuleName = Literal[
    'makerdao_dsr',
    'makerdao_vaults',
    'aave',
    'compound',
    'yearn_vaults',
    'uniswap',
    'adex',
]
AVAILABLE_MODULES = [
    'makerdao_dsr',
    'makerdao_vaults',
    'aave',
    'compound',
    'yearn_vaults',
    'uniswap',
    'adex',
]

T_BinaryEthAddress = bytes
BinaryEthAddress = NewType('BinaryEthAddress', T_BinaryEthAddress)


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


class ApiCredentials(NamedTuple):
    """Represents Credentials for various APIs. Exchanges, Premium e.t.c.

    The Api in question must at least have an API key and an API secret.
    """
    api_key: ApiKey
    api_secret: ApiSecret
    passphrase: Optional[str] = None

    @staticmethod
    def serialize(
            api_key: str,
            api_secret: str,
            passphrase: Optional[str] = None,
    ) -> 'ApiCredentials':
        return ApiCredentials(
            api_key=ApiKey(api_key),
            api_secret=ApiSecret(str.encode(api_secret)),
            passphrase=passphrase,
        )


class ExternalService(Enum):
    ETHERSCAN = 0
    CRYPTOCOMPARE = 1
    BEACONCHAIN = 2

    @staticmethod
    def serialize(name: str) -> Optional['ExternalService']:
        if name == 'etherscan':
            return ExternalService.ETHERSCAN
        if name == 'cryptocompare':
            return ExternalService.CRYPTOCOMPARE
        if name == 'beaconchain':
            return ExternalService.BEACONCHAIN
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

BlockchainAddress = Union[EthAddress, BTCAddress, ChecksumEthAddress, str]
ListOfBlockchainAddresses = Union[List[BTCAddress], List[ChecksumEthAddress]]


class EthTokenInfo(NamedTuple):
    identifier: str
    address: ChecksumEthAddress
    symbol: str
    name: str
    decimals: int


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


class ResultCache(NamedTuple):
    """Represents a time-cached result of some API query"""
    result: Dict
    timestamp: Timestamp


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
    # this is an internal transaction returned by etherscan
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
        return hash(self.tx_hash.hex() + self.from_address + str(self.nonce))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if not isinstance(other, EthereumTransaction):
            return False

        return hash(self) == hash(other)


class SupportedBlockchain(Enum):
    """These are the blockchains for which account tracking is supported """
    ETHEREUM = 'ETH'
    BITCOIN = 'BTC'

    def get_address_type(self) -> Callable:
        if self == SupportedBlockchain.ETHEREUM:
            return ChecksumEthAddress
        if self == SupportedBlockchain.BITCOIN:
            return BTCAddress
        # else
        raise AssertionError('Invalid SupportedBlockchain value')


class AssetType(Enum):
    FIAT = 1
    OWN_CHAIN = 2
    ETH_TOKEN = 3
    OMNI_TOKEN = 4
    NEO_TOKEN = 5
    XCP_TOKEN = 6
    BTS_TOKEN = 7
    ARDOR_TOKEN = 8
    NXT_TOKEN = 9
    UBIQ_TOKEN = 10
    NUBITS_TOKEN = 11
    BURST_TOKEN = 12
    WAVES_TOKEN = 13
    QTUM_TOKEN = 14
    STELLAR_TOKEN = 15
    TRON_TOKEN = 16
    ONTOLOGY_TOKEN = 17
    ETH_TOKEN_AND_MORE = 18
    EXCHANGE_SPECIFIC = 19
    VECHAIN_TOKEN = 20
    BINANCE_TOKEN = 21
    EOS_TOKEN = 22
    FUSION_TOKEN = 23


class AssetData(NamedTuple):
    """Data of an asset. Keep in sync with assets/asset.py"""
    identifier: str
    name: str
    symbol: str
    active: bool
    asset_type: AssetType
    # Every asset should have a started timestamp except for FIAT which are
    # most of the times older than epoch
    started: Optional[Timestamp]
    ended: Optional[Timestamp]
    forked: Optional[str]
    swapped_for: Optional[str]
    ethereum_address: Optional[ChecksumEthAddress]
    decimals: Optional[int]
    # None means, no special mapping. '' means not supported
    cryptocompare: Optional[str]
    coingecko: Optional[str]


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


class Location(Enum):
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
    ADEX = 19

    def __str__(self) -> str:
        if self == Location.EXTERNAL:
            return 'external'
        if self == Location.KRAKEN:
            return 'kraken'
        if self == Location.POLONIEX:
            return 'poloniex'
        if self == Location.BITTREX:
            return 'bittrex'
        if self == Location.BINANCE:
            return 'binance'
        if self == Location.BITMEX:
            return 'bitmex'
        if self == Location.COINBASE:
            return 'coinbase'
        if self == Location.TOTAL:
            return 'total'
        if self == Location.BANKS:
            return 'banks'
        if self == Location.BLOCKCHAIN:
            return 'blockchain'
        if self == Location.COINBASEPRO:
            return 'coinbasepro'
        if self == Location.GEMINI:
            return 'gemini'
        if self == Location.EQUITIES:
            return 'equities'
        if self == Location.REALESTATE:
            return 'real estate'
        if self == Location.COMMODITIES:
            return 'commodities'
        if self == Location.CRYPTOCOM:
            return 'crypto.com'
        if self == Location.UNISWAP:
            return 'uniswap'
        if self == Location.BITSTAMP:
            return 'bitstamp'
        if self == Location.ADEX:
            return 'adex'
        # else
        raise RuntimeError(f'Corrupt value {self} for Location -- Should never happen')

    def serialize_for_db(self) -> str:
        if self == Location.EXTERNAL:
            return 'A'
        if self == Location.KRAKEN:
            return 'B'
        if self == Location.POLONIEX:
            return 'C'
        if self == Location.BITTREX:
            return 'D'
        if self == Location.BINANCE:
            return 'E'
        if self == Location.BITMEX:
            return 'F'
        if self == Location.COINBASE:
            return 'G'
        if self == Location.TOTAL:
            return 'H'
        if self == Location.BANKS:
            return 'I'
        if self == Location.BLOCKCHAIN:
            return 'J'
        if self == Location.COINBASEPRO:
            return 'K'
        if self == Location.GEMINI:
            return 'L'
        if self == Location.EQUITIES:
            return 'M'
        if self == Location.REALESTATE:
            return 'N'
        if self == Location.COMMODITIES:
            return 'O'
        if self == Location.CRYPTOCOM:
            return 'P'
        if self == Location.UNISWAP:
            return 'Q'
        if self == Location.BITSTAMP:
            return 'R'
        if self == Location.ADEX:
            return 'S'
        # else
        raise RuntimeError(f'Corrupt value {self} for Location -- Should never happen')


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
