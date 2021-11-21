import json
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, NewType, Optional, Tuple, Union

import jsonschema
from eth_typing import ChecksumAddress
from typing_extensions import Literal

from rotkehlchen.errors import DeserializationError, EncodingError
from rotkehlchen.fval import FVal
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn  # lgtm[py/unsafe-cyclic-import]
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

from rotkehlchen.chain.substrate.typing import KusamaAddress, PolkadotAddress  # isort:skip # lgtm [py/unsafe-cyclic-import]  # noqa: E501

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
    'sushiswap',
    'liquity',
    'pickle_finance',
    'nfts',
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
    'sushiswap': 'Sushiswap',
    'liquity': 'Liquity',
    'pickle_finance': 'Pickle Finance',
    'nfts': 'NFTs',
}


IMPORTABLE_LOCATIONS = Literal[
    'cointracking.info',
    'cryptocom',
    'blockfi-transactions',
    'blockfi-trades',
    'nexo',
    'gitcoin',
    'shapeshift-trades',
    'uphold',
    'bisq',
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


class ExternalService(SerializableEnumMixin):
    ETHERSCAN = 0
    CRYPTOCOMPARE = 1
    BEACONCHAIN = 2
    LOOPRING = 3
    OPENSEA = 4
    COVALENT = 5


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

T_Eth2PubKey = str
Eth2PubKey = NewType('Eth2PubKey', T_Eth2PubKey)

BlockchainAddress = Union[
    EthAddress,
    BTCAddress,
    ChecksumEthAddress,
    KusamaAddress,
    PolkadotAddress,
    str,
]
ListOfBlockchainAddresses = Union[
    List[BTCAddress],
    List[ChecksumEthAddress],
    List[KusamaAddress],
    List[PolkadotAddress],
]


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


class CovalentTransaction(NamedTuple):
    """Represent a transaction in covalent"""
    tx_hash: str
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEthAddress
    to_address: Optional[ChecksumEthAddress]
    value: int
    gas: int
    gas_price: int
    gas_used: int
    # Input data and nonce is decoded, default is 0x and 0, encoded in future
    input_data: str
    nonce: int

    def serialize(self) -> Dict[str, Any]:
        result = {
            'tx_hash': self.tx_hash,
            'timestamp': self.timestamp,
            'block_number': self.block_number,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'value': self.value,
            'gas': self.gas,
            'gas_price': self.gas_price,
            'gas_used': self.gas_used,
            'input_data': self.input_data,
            'nonce': self.nonce,
        }

        return result

    def __hash__(self) -> int:
        return hash(self.identifier)

    def __eq__(self, other: Any) -> bool:
        if other is None or not isinstance(other, CovalentTransaction):
            return False

        return hash(self) == hash(other)

    @property
    def identifier(self) -> str:
        return self.tx_hash + self.from_address.replace('0x', '') + str(self.nonce)


class SupportedBlockchain(Enum):
    """These are the blockchains for which account tracking is supported """
    ETHEREUM = 'ETH'
    ETHEREUM_BEACONCHAIN = 'ETH2'
    BITCOIN = 'BTC'
    KUSAMA = 'KSM'
    AVALANCHE = 'AVAX'
    POLKADOT = 'DOT'

    def get_address_type(self) -> Callable:
        if self in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.AVALANCHE):
            return ChecksumEthAddress
        if self == SupportedBlockchain.ETHEREUM_BEACONCHAIN:
            return Eth2PubKey
        if self == SupportedBlockchain.BITCOIN:
            return BTCAddress
        if self == SupportedBlockchain.KUSAMA:
            return KusamaAddress
        if self == SupportedBlockchain.POLKADOT:
            return PolkadotAddress
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
        if self == SupportedBlockchain.POLKADOT:
            return 354
        if self == SupportedBlockchain.AVALANCHE:
            return 9000
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
    SUSHISWAP = 31
    SHAPESHIFT = 32
    UPHOLD = 33
    BITPANDA = 34
    BISQ = 35


class AssetMovementCategory(DBEnumMixIn):
    """Supported Asset Movement Types so far only deposit and withdrawals"""
    DEPOSIT = 1
    WITHDRAWAL = 2


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


class SchemaEventType(Enum):
    """Supported schemas"""
    ACCOUNTING_HISTORY = 1
    ACCOUNTING_OVERVIEW = 2
    ACCOUNTING_EVENT = 3

    def serialize_for_db(self) -> str:
        if self == SchemaEventType.ACCOUNTING_OVERVIEW:
            return 'accounting_overview'
        if self == SchemaEventType.ACCOUNTING_EVENT:
            return 'accounting_event'
        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')

    @classmethod
    def deserialize_from_db(
            cls,
            value: str,
    ) -> 'SchemaEventType':
        """May raise DeserializationError if anything is wrong"""
        if value == 'accounting_overview':
            return SchemaEventType.ACCOUNTING_OVERVIEW
        if value == 'accounting_event':
            return SchemaEventType.ACCOUNTING_EVENT

        raise DeserializationError(f'Unexpected value {value} at JsonSchema deserialization')

    def __str__(self) -> str:
        if self == SchemaEventType.ACCOUNTING_OVERVIEW:
            return 'accounting_overview'
        if self == SchemaEventType.ACCOUNTING_EVENT:
            return 'accounting_event'
        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')

    def serialize(self) -> Dict[str, Any]:
        """May raise EncodingError if schema is invalid"""
        try:
            schema: Dict[str, Any] = {}
            if self == SchemaEventType.ACCOUNTING_OVERVIEW:
                schema = {
                    'type': 'object',
                    'properties': {
                        'ledger_actions_profit_loss': {'type': 'string'},
                        'defi_profit_loss': {'type': 'string'},
                        'loan_profit': {'type': 'string'},
                        'margin_positions_profit_loss': {'type': 'string'},
                        'settlement_losses': {'type': 'string'},
                        'ethereum_transaction_gas_costs': {'type': 'string'},
                        'asset_movement_fees': {'type': 'string'},
                        'general_trade_profit_loss': {'type': 'string'},
                        'taxable_trade_profit_loss': {'type': 'string'},
                        'total_taxable_profit_loss': {'type': 'string'},
                        'total_profit_loss': {'type': 'string'},
                    },
                    'required': [
                        'ledger_actions_profit_loss',
                        'defi_profit_loss',
                        'loan_profit',
                        'margin_positions_profit_loss',
                        'settlement_losses',
                        'ethereum_transaction_gas_costs',
                        'asset_movement_fees',
                        'general_trade_profit_loss',
                        'taxable_trade_profit_loss',
                        'total_taxable_profit_loss',
                        'total_profit_loss',
                    ]}
            if self == SchemaEventType.ACCOUNTING_EVENT:
                schema = {
                    'type': 'object',
                    'properties': {
                        'event_type': {'type': 'string'},
                        'location': {'type': 'string'},
                        'paid_in_profit_currency': {'type': 'string'},
                        'paid_asset': {'type': 'string'},
                        'paid_in_asset': {'type': 'string'},
                        'taxable_amount': {'type': 'string'},
                        'taxable_bought_cost_in_profit_currency': {'type': 'string'},
                        'received_asset': {'type': 'string'},
                        'taxable_received_in_profit_currency': {'type': 'string'},
                        'received_in_asset': {'type': 'string'},
                        'net_profit_or_loss': {'type': 'string'},
                        'time': {'type': 'number'},
                        'cost_basis': {
                            'oneOf': [{'type': 'null'}, {'$ref': '#/$defs/cost_basis'}],
                        },
                        'is_virtual': {'type': 'boolean'},
                        'link': {'oneOf': [{'type': 'string'}, {'type': 'null'}]},
                        'notes': {'oneOf': [{'type': 'string'}, {'type': 'null'}]},
                    },
                    '$defs': {
                        'cost_basis': {
                            'type': 'object',
                            'properties': {
                                'is_complete': {'type': 'boolean'},
                                'matched_acquisitions': {'type': 'array'},
                                'taxable_bought_cost': {'type': 'string'},
                                'taxfree_bought_cost': {'type': 'string'},
                            },
                        },
                    },
                    'required': [
                        'location',
                        'paid_in_profit_currency',
                        'paid_in_asset',
                        'taxable_amount',
                        'taxable_bought_cost_in_profit_currency',
                        'taxable_received_in_profit_currency',
                        'received_in_asset',
                        'net_profit_or_loss',
                        'time',
                        'cost_basis',
                        'is_virtual',
                        'link',
                        'notes',
                    ]}

            jsonschema.Draft4Validator.check_schema(schema)
            return schema

        except jsonschema.exceptions.SchemaError as e:
            raise EncodingError(f'Could not serialize the SchemaEventType. Invalid schema: {e}')  # noqa E501


NamedJsonDBTuple = (
    Tuple[
        str,  # type,
        str,  # data
    ]
)


class NamedJson(NamedTuple):
    event_type: SchemaEventType
    data: Dict[str, Any]

    @classmethod
    def deserialize_from_db(
            cls,
            json_tuple: NamedJsonDBTuple,
    ) -> 'NamedJson':
        """Turns a tuple read from the database into an appropriate JsonSchema.
        May raise:
         - a DeserializationError if something is wrong with the DB data or json validation fails.
        Event_tuple index - Schema columns
        ----------------------------------
        0 - event_type
        1 - data
        """
        try:
            event_type: SchemaEventType = SchemaEventType.deserialize_from_db(json_tuple[0])  # noqa E501
            schema: Dict[str, Any] = event_type.serialize()
            data = json.loads(json_tuple[1])
            jsonschema.validate(data, schema)
            return NamedJson(
                event_type=event_type,
                data=data)

        except jsonschema.exceptions.ValidationError as e:
            raise DeserializationError(
                f'Failed jsonschema validation of NamedJson: {json_tuple[0]} data {json_tuple[1]}:'
                f'Error was {str(e)}')
        except json.decoder.JSONDecodeError as e:
            raise DeserializationError(
                f'Could not decode json for {json_tuple} at NamedJson deserialization: {str(e)}')

    def to_db_tuple(self) -> NamedJsonDBTuple:
        """May raise:
        - ValueError if jsonschema validation fails
        - EncodingError if validation somehow passed and the value still could not be encoded"""
        try:
            schema: Dict[str, Any] = self.event_type.serialize()
            jsonschema.validate(self.data, schema)
            return (
                self.event_type.serialize_for_db(),
                json.dumps(self.data),
            )
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(
                f'Failed jsonschema validation of NamedJson: {str(e)}')
        except TypeError as e:
            raise EncodingError(
                f'Could not encode json for NamedJson: {str(e)}')

    def serialize(self) -> Dict[str, Any]:
        """May raise:
        - ValueError if jsonschema validation fails
        - EncodingError if validation somehow passed and the value still could not be encoded"""
        try:
            schema: Dict[str, Any] = self.event_type.serialize()
            jsonschema.validate(self.data, schema)
            return {
                'event_type': str(self.event_type),
                'data': json.dumps(self.data),
            }
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(
                f'Failed jsonschema validation of NamedJson: {str(e)}')
        except TypeError as e:
            raise EncodingError(
                f'Could not encode json for NamedJson: {str(e)}')


EXTERNAL_EXCHANGES: List = [
    Location.CRYPTOCOM,
    Location.BLOCKFI,
    Location.NEXO,
    Location.SHAPESHIFT,
    Location.UPHOLD,
    Location.BISQ,
]
EXTERNAL_LOCATION = [Location.EXTERNAL] + EXTERNAL_EXCHANGES
