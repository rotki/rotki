
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, NewType, Optional, Tuple, Union

from eth_utils.typing import ChecksumAddress
from typing_extensions import Literal

from rotkehlchen.fval import FVal

ModuleName = Literal['makerdao_dsr', 'makerdao_vaults', 'aave', 'compound', 'yearn_vaults', 'uniswap']
AVAILABLE_MODULES = ['makerdao_dsr', 'makerdao_vaults', 'aave', 'compound', 'yearn_vaults', 'uniswap']

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

    @staticmethod
    def serialize(name: str) -> Optional['ExternalService']:
        if name == 'etherscan':
            return ExternalService.ETHERSCAN
        elif name == 'cryptocompare':
            return ExternalService.CRYPTOCOMPARE

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
        elif self == SupportedBlockchain.BITCOIN:
            return BTCAddress

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
        elif self == TradeType.SELL:
            return 'sell'
        elif self == TradeType.SETTLEMENT_BUY:
            return 'settlement_buy'
        elif self == TradeType.SETTLEMENT_SELL:
            return 'settlement_sell'

        raise RuntimeError(f'Corrupt value {self} for TradeType -- Should never happen')

    def serialize_for_db(self) -> str:
        if self == TradeType.BUY:
            return 'A'
        elif self == TradeType.SELL:
            return 'B'
        elif self == TradeType.SETTLEMENT_BUY:
            return 'C'
        elif self == TradeType.SETTLEMENT_SELL:
            return 'D'

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

    def __str__(self) -> str:
        if self == Location.EXTERNAL:
            return 'external'
        elif self == Location.KRAKEN:
            return 'kraken'
        elif self == Location.POLONIEX:
            return 'poloniex'
        elif self == Location.BITTREX:
            return 'bittrex'
        elif self == Location.BINANCE:
            return 'binance'
        elif self == Location.BITMEX:
            return 'bitmex'
        elif self == Location.COINBASE:
            return 'coinbase'
        elif self == Location.TOTAL:
            return 'total'
        elif self == Location.BANKS:
            return 'banks'
        elif self == Location.BLOCKCHAIN:
            return 'blockchain'
        elif self == Location.COINBASEPRO:
            return 'coinbasepro'
        elif self == Location.GEMINI:
            return 'gemini'
        elif self == Location.EQUITIES:
            return 'equities'
        elif self == Location.REALESTATE:
            return 'real estate'
        elif self == Location.COMMODITIES:
            return 'commodities'
        elif self == Location.CRYPTOCOM:
            return 'crypto.com'

        raise RuntimeError(f'Corrupt value {self} for Location -- Should never happen')

    def serialize_for_db(self) -> str:
        if self == Location.EXTERNAL:
            return 'A'
        elif self == Location.KRAKEN:
            return 'B'
        elif self == Location.POLONIEX:
            return 'C'
        elif self == Location.BITTREX:
            return 'D'
        elif self == Location.BINANCE:
            return 'E'
        elif self == Location.BITMEX:
            return 'F'
        elif self == Location.COINBASE:
            return 'G'
        elif self == Location.TOTAL:
            return 'H'
        elif self == Location.BANKS:
            return 'I'
        elif self == Location.BLOCKCHAIN:
            return 'J'
        elif self == Location.COINBASEPRO:
            return 'K'
        elif self == Location.GEMINI:
            return 'L'
        elif self == Location.EQUITIES:
            return 'M'
        elif self == Location.REALESTATE:
            return 'N'
        elif self == Location.COMMODITIES:
            return 'O'
        elif self == Location.CRYPTOCOM:
            return 'P'

        raise RuntimeError(f'Corrupt value {self} for Location -- Should never happen')


class AssetMovementCategory(Enum):
    """Supported Asset Movement Types so far only deposit and withdrawals"""
    DEPOSIT = 1
    WITHDRAWAL = 2

    def __str__(self) -> str:
        if self == AssetMovementCategory.DEPOSIT:
            return 'deposit'
        elif self == AssetMovementCategory.WITHDRAWAL:
            return 'withdrawal'

        raise RuntimeError(
            f'Corrupt value {self} for AssetMovementCategory -- Should never happen',
        )

    def serialize_for_db(self) -> str:
        if self == AssetMovementCategory.DEPOSIT:
            return 'A'
        elif self == AssetMovementCategory.WITHDRAWAL:
            return 'B'

        raise RuntimeError(
            f'Corrupt value {self} for AssetMovementCategory -- Should never happen',
        )


class BlockchainAccountData(NamedTuple):
    address: BlockchainAddress
    label: Optional[str] = None
    tags: Optional[List[str]] = None


class BalanceType(Enum):
    """The type of balance. Asset for lending balances and Debt for borrowing"""
    ASSET = 1
    DEBT = 2

    def __str__(self) -> str:
        if self == BalanceType.ASSET:
            return 'asset'
        elif self == BalanceType.DEBT:
            return 'debt'

        raise RuntimeError(
            f'Corrupt value {self} for AssetMovementCategory -- Should never happen',
        )
