from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, NewType, Optional, Tuple, Union

from eth_typing import ChecksumAddress
from typing_extensions import Literal

from rotkehlchen.chain.substrate.typing import KusamaAddress
from rotkehlchen.fval import FVal

ModuleName = Literal[
    'makerdao_dsr',
    'makerdao_vaults',
    'aave',
    'compound',
    'yearn_vaults',
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
    'uniswap': 'Uniswap',
    'adex': 'AdEx',
    'loopring': 'Loopring',
    'balancer': 'Balancer',
    'eth2': 'Eth2',
}

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
    BINANCE_US = 19
    BITFINEX = 20
    BITCOINDE = 21
    ICONOMI = 22
    KUCOIN = 23
    BALANCER = 24
    LOOPRING = 25
    FTX = 26

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
            return 'realestate'
        if self == Location.COMMODITIES:
            return 'commodities'
        if self == Location.CRYPTOCOM:
            return 'crypto.com'
        if self == Location.UNISWAP:
            return 'uniswap'
        if self == Location.BITSTAMP:
            return 'bitstamp'
        if self == Location.BINANCE_US:
            return 'binance_us'
        if self == Location.BITFINEX:
            return 'bitfinex'
        if self == Location.BITCOINDE:
            return 'bitcoinde'
        if self == Location.ICONOMI:
            return 'iconomi'
        if self == Location.KUCOIN:
            return 'kucoin'
        if self == Location.BALANCER:
            return 'balancer'
        if self == Location.LOOPRING:
            return 'loopring'
        if self == Location.FTX:
            return 'ftx'
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
        if self == Location.BINANCE_US:
            return 'S'
        if self == Location.BITFINEX:
            return 'T'
        if self == Location.BITCOINDE:
            return 'U'
        if self == Location.ICONOMI:
            return 'V'
        if self == Location.KUCOIN:
            return 'W'
        if self == Location.BALANCER:
            return 'X'
        if self == Location.LOOPRING:
            return 'Y'
        if self == Location.FTX:
            return 'Z'
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
