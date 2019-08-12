from enum import Enum
from typing import Dict, NamedTuple, NewType, Optional, TypeVar, Union

from eth_utils.typing import ChecksumAddress

from rotkehlchen.fval import FVal

T_BinaryEthAddress = bytes
BinaryEthAddress = NewType('BinaryEthAddress', T_BinaryEthAddress)


T_Timestamp = int
Timestamp = NewType('Timestamp', T_Timestamp)

T_ApiKey = bytes
ApiKey = NewType('ApiKey', T_ApiKey)

T_ApiSecret = bytes
ApiSecret = NewType('ApiSecret', T_ApiSecret)

T_B64EncodedBytes = bytes
B64EncodedBytes = NewType('B64EncodedBytes', T_B64EncodedBytes)

T_B64EncodedString = str
B64EncodedString = NewType('B64EncodedString', T_B64EncodedString)


class ApiCredentials(NamedTuple):
    """Represents Credentials for various APIs. Exchanges, Premium e.t.c."""
    api_key: ApiKey
    api_secret: ApiSecret

    @staticmethod
    def serialize(api_key: str, api_secret: str) -> 'ApiCredentials':
        return ApiCredentials(
            api_key=ApiKey(str.encode(api_key)),
            api_secret=ApiSecret(str.encode(api_secret)),
        )


T_FilePath = str
FilePath = NewType('FilePath', T_FilePath)

T_TradePair = str
TradePair = NewType('TradePair', T_TradePair)

T_FiatAsset = str
FiatAsset = NewType('FiatAsset', T_FiatAsset)

T_EthAddres = str
EthAddress = NewType('EthAddress', T_EthAddres)

ChecksumEthAddress = ChecksumAddress

T_BTCAddress = str
BTCAddress = NewType('BTCAddress', T_BTCAddress)

BlockchainAddress = Union[EthAddress, BTCAddress, ChecksumEthAddress]


class EthTokenInfo(NamedTuple):
    address: ChecksumEthAddress
    symbol: str
    name: str
    decimal: int


T_EmptyStr = str
EmptyStr = NewType('EmptyStr', T_EmptyStr)

T_Fee = FVal
Fee = NewType('Fee', T_Fee)

T_Price = FVal
Price = NewType('Price', T_Price)

T_AssetAmount = FVal
AssetAmount = NewType('AssetAmount', T_AssetAmount)

# Types that can go in functions that have
# things that can be calculated such as amount, fees, price e.t.c.
Numerical = TypeVar('Numerical', FVal, AssetAmount, Fee, Price)


class ResultCache(NamedTuple):
    """Represents a time-cached result of some API query"""
    result: Dict
    timestamp: Timestamp


T_EventType = str
EventType = NewType('EventType', T_EventType)


class EthereumTransaction(NamedTuple):
    """Represent an Ethereum transaction"""
    timestamp: Timestamp
    block_number: int
    hash: bytes
    from_address: EthAddress
    to_address: EthAddress
    value: FVal
    gas: FVal
    gas_price: FVal
    gas_used: FVal


class SupportedBlockchain(Enum):
    """These are the blockchains for which account tracking is supported """
    ETHEREUM = 'ETH'
    BITCOIN = 'BTC'


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


class TradeType(Enum):
    BUY = 1
    SELL = 2
    SETTLEMENT_BUY = 3
    SETTLEMENT_SELL = 4

    def __str__(self) -> str:
        if self == TradeType.BUY:
            return 'buy'
        elif self == TradeType.SELL:
            return 'sell'
        elif self == TradeType.SETTLEMENT_BUY:
            return 'settlement_buy'
        elif self == TradeType.SETTLEMENT_SELL:
            return 'settlement_sell'

        raise RuntimeError(f'Corrupt value {self} for TradeType -- Should never happen')


class Exchange(Enum):
    """Supported Exchanges"""
    KRAKEN = 0
    POLONIEX = 1
    BITTREX = 2
    BINANCE = 3
    BITMEX = 4

    def __str__(self) -> str:
        if self == Exchange.KRAKEN:
            return 'kraken'
        elif self == Exchange.POLONIEX:
            return 'poloniex'
        elif self == Exchange.BITTREX:
            return 'bittrex'
        elif self == Exchange.BINANCE:
            return 'binance'
        elif self == Exchange.BITMEX:
            return 'bitmex'

        raise RuntimeError(f'Corrupt value {self} for Exchange -- Should never happen')
