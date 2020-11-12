from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import (
    Any,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Set,
    Tuple,
    Type,
    Union,
)

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.assets.unknown_asset import (
    FakeAsset,
    UnknownEthereumToken,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_address,
    deserialize_ethereum_token_from_db,
    deserialize_fee,
    deserialize_location_from_db,
    deserialize_price,
    deserialize_timestamp,
    deserialize_trade_type_from_db,
    deserialize_unknown_ethereum_token_from_db,
)
from rotkehlchen.typing import (
    AssetAmount,
    ChecksumEthAddress,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeID,
    TradePair,
    TradeType,
)

log = logging.getLogger(__name__)


CUSTOM_TRADE_ID_NO_GROUPS = 10
# A regex is essential for extracting the custom ID data. `split()` is not
# reliable due to separator characters in assets names and symbols
CUSTOM_TRADE_ID_REGEX = re.compile(
    r'^(0x[a-fA-F0-9]{40})_'  # address
    r'(0|1)_(0x[a-fA-F0-9]{40})_(.*)_(\d+)_'  # base_asset data
    r'(0|1)_(0x[a-fA-F0-9]{40})_(.*)_(\d+)_'  # quote_asset data
    r'(.*)$',  # partial_id
)
SWAP_FEE = FVal('0.003')  # 0.3% fee for swapping tokens
UNISWAP_TRADES_PREFIX = f'{Location.UNISWAP}_trades'


class AMMTradeIDError(Exception):
    pass


# Get balances


@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    asset: Union[EthereumToken, UnknownEthereumToken]
    total_amount: FVal
    user_balance: Balance
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict[str, Any]:
        serialized_asset: Union[str, Dict[str, Any]]

        if isinstance(self.asset, EthereumToken):
            serialized_asset = self.asset.serialize()
        elif isinstance(self.asset, UnknownEthereumToken):
            unk_asset_keys = ('ethereum_address', 'name', 'symbol')
            serialized_asset = self.asset.serialize_as_dict(keys=unk_asset_keys)
        else:
            raise AssertionError(
                f'Got type {type(self.asset)} for a LiquidityPool Asset. '
                f'This should never happen.',
            )

        return {
            'asset': serialized_asset,
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
        }


@dataclass(init=True, repr=True)
class LiquidityPool:
    address: ChecksumEthAddress
    assets: List[LiquidityPoolAsset]
    total_supply: FVal
    user_balance: Balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'assets': [asset.serialize() for asset in self.assets],
            'total_supply': self.total_supply,
            'user_balance': self.user_balance.serialize(),
        }


AddressBalances = Dict[ChecksumEthAddress, List[LiquidityPool]]
DDAddressBalances = DefaultDict[ChecksumEthAddress, List[LiquidityPool]]
AssetPrice = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_balances: AddressBalances
    known_assets: Set[EthereumToken]
    unknown_assets: Set[UnknownEthereumToken]


# Get History

TradeDBTuple = (
    Tuple[
        str,  # identifier
        int,  # timestamp
        str,  # location
        str,  # pair
        str,  # type
        str,  # amount
        str,  # rate
        str,  # fee
        str,  # fee_currency
        str,  # link
        str,  # notes
    ]
)


class AMMTrade(NamedTuple):
    """This class aims for a better trades support than the current Trade class
    in AMMs protocols.

    It aims for backwards compatibility with Trade in CRUD DB operations.
    """
    tx_hash: str  # Swap.transaction.id
    address: ChecksumEthAddress  # Swap.to
    timestamp: Timestamp  # Swap.timestamp
    trade_type: TradeType  # SELL if Swap.amount1In > 0, BUY if Swap.amount0In == 0
    base_asset: Union[EthereumToken, UnknownEthereumToken]  # Swap.pair.token0
    quote_asset: Union[EthereumToken, UnknownEthereumToken]  # Swap.pair.token1
    amount: AssetAmount  # Swap.amount0In if SELL, Swap.amount0Out if BUY
    rate: Price  # Swap.pair.token0Price if SELL, Swap.pair.token1Price if BUY
    fee: Fee  # amount * 0.3% fee
    fee_currency: FakeAsset  # from base_asset.symbol
    location: Location = Location.UNISWAP
    notes: str = ''

    @classmethod
    def get_ammtrade_from_trade_db_tuple(
            cls,
            trade_tuple: TradeDBTuple,
    ) -> AMMTrade:
        """Turns a tuple read from DB into an appropriate Trade.

        May raise a DeserializationError if something is wrong with the DB data

        Trade_tuple index - Schema columns
        ----------------------------------
         0 - identifier
         1 - timestamp
         2 - location
         3 - pair
         4 - type
         5 - amount
         6 - rate
         7 - fee
         8 - fee_currency
         9 - link
        10 - notes
        """
        # Get assets' data from `identifier`, `ba` (base) and `qa` (quote)
        identifier = trade_tuple[0]
        match = CUSTOM_TRADE_ID_REGEX.match(identifier)
        if not match or len(match.groups()) != CUSTOM_TRADE_ID_NO_GROUPS:
            log.error(
                f'Failed to extract TradeAMM identifier data from existing'
                f'Trade identifier: {identifier}.',
            )
            raise DeserializationError('Failed to deserialize TradeAMM identifier')

        (
            address,
            is_ba_unknown,
            ba_address,
            ba_name,
            ba_decimals,
            is_qa_unknown,
            qa_address,
            qa_name,
            qa_decimals,
            _,  # partial_id
        ) = match.groups()

        address = deserialize_ethereum_address(address)

        # Get assets' instances
        ba_symbol, qa_symbol = trade_tuple[3].split('_')  # from pair
        base_asset: Union[EthereumToken, UnknownEthereumToken] = (
            deserialize_unknown_ethereum_token_from_db(
                ethereum_address=ba_address,
                symbol=ba_symbol,
                name=ba_name,
                decimals=int(ba_decimals),
            )
            if is_ba_unknown
            else deserialize_ethereum_token_from_db(identifier=ba_symbol)
        )
        quote_asset: Union[EthereumToken, UnknownEthereumToken] = (
            deserialize_unknown_ethereum_token_from_db(
                ethereum_address=qa_address,
                symbol=qa_symbol,
                name=qa_name,
                decimals=int(qa_decimals),
            )
            if is_qa_unknown
            else deserialize_ethereum_token_from_db(identifier=qa_symbol)
        )

        return cls(
            tx_hash=trade_tuple[9],
            address=address,
            timestamp=deserialize_timestamp(trade_tuple[1]),
            location=deserialize_location_from_db(trade_tuple[2]),
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=deserialize_trade_type_from_db(trade_tuple[4]),
            amount=deserialize_asset_amount(trade_tuple[5]),
            rate=deserialize_price(trade_tuple[6]),
            fee=deserialize_fee(trade_tuple[7]),
            fee_currency=FakeAsset(identifier=trade_tuple[8]),
            notes=trade_tuple[10],
        )

    @classmethod
    def get_ammtrade_from_trade(cls, trade: Trade) -> AMMTrade:
        """Turns a Trade to an AMMTrade
        """
        # Get assets' data from `identifier`, `ba` (base) and `qa` (quote)
        match = CUSTOM_TRADE_ID_REGEX.match(trade.identifier)
        if not match or len(match.groups()) != CUSTOM_TRADE_ID_NO_GROUPS:
            log.error(
                f'Failed to extract TradeAMM identifier data from existing'
                f'Trade identifier: {trade.identifier}.',
            )
            raise AMMTradeIDError('Failed to get TradeAMM identifier from Trade identifier')

        (
            address,
            is_ba_unknown,
            ba_address,
            ba_name,
            ba_decimals,
            is_qa_unknown,
            qa_address,
            qa_name,
            qa_decimals,
            _,  # partial_id
        ) = match.groups()

        address = deserialize_ethereum_address(address)
        ba_address = deserialize_ethereum_address(ba_address)
        qa_address = deserialize_ethereum_address(qa_address)

        # Get assets' instances
        ba_symbol, qa_symbol = trade.pair.split('_')
        base_asset: Union[EthereumToken, UnknownEthereumToken] = (
            UnknownEthereumToken(
                ethereum_address=ba_address,
                symbol=ba_symbol,
                name=ba_name,
                decimals=int(ba_decimals),
            )
            if is_ba_unknown
            else EthereumToken(identifier=ba_symbol)
        )
        quote_asset: Union[EthereumToken, UnknownEthereumToken] = (
            UnknownEthereumToken(
                ethereum_address=qa_address,
                symbol=qa_symbol,
                name=qa_name,
                decimals=int(qa_decimals),
            )
            if is_qa_unknown
            else EthereumToken(identifier=qa_symbol)
        )
        return cls(
            tx_hash=trade.link,
            address=address,
            timestamp=trade.timestamp,
            location=trade.location,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade.trade_type,
            amount=trade.amount,
            rate=trade.rate,
            fee=trade.fee,
            fee_currency=FakeAsset(identifier=trade.fee_currency.identifier),
            notes=trade.notes,
        )

    def get_trade_from_ammtrade(self) -> Trade:
        """Turns an AMMTrade to a Trade
        """
        # Get `fee_currency` symbol and class to instantiate
        fc_class: Union[Type[Asset], Type[FakeAsset]]
        if self.trade_type == TradeType.SELL:
            fc_identifier = self.base_asset.symbol
            fc_class = (
                Asset
                if isinstance(self.base_asset, EthereumToken)
                else FakeAsset
            )
        else:
            fc_identifier = self.quote_asset.symbol
            fc_class = (
                Asset
                if isinstance(self.quote_asset, EthereumToken)
                else FakeAsset
            )
        return Trade(
            timestamp=self.timestamp,
            location=self.location,
            pair=TradePair(self.pair),
            trade_type=self.trade_type,
            amount=self.amount,
            rate=self.rate,
            fee=self.fee,
            fee_currency=fc_class(identifier=fc_identifier),  # type: ignore
            link=self.tx_hash,
            notes=self.notes,
            custom_identifier=self.identifier,
        )

    @property
    def identifier(self) -> TradeID:
        """Formulates a unique identifier for the trade to become the DB primary key

        Current `trades` table and `Trade` class (from `data_structures.py`)
        do not support/are not compatible with:
          - Storing the ethereum address that did the trade.
          - Unknown ethereum tokens, and both `pair` assets are expected to be
          known (i.e. <Asset>).

        For the reasons above, a custom trade identifier that contains the
        the previous data.
        """
        partial_id = (
            str(self.location) +
            str(self.timestamp) +
            str(self.trade_type) +
            self.pair +
            str(self.amount) +
            str(self.rate) +
            self.link
        )
        ba_, qa_ = self.base_asset, self.quote_asset
        is_ba_unknown = 0 if isinstance(ba_, EthereumToken) else 1
        is_qa_unknown = 0 if isinstance(qa_, EthereumToken) else 1

        return TradeID(
            f'{self.address}_'
            f'{is_ba_unknown}_{ba_.ethereum_address}_{ba_.name}_{ba_.decimals}_'
            f'{is_qa_unknown}_{qa_.ethereum_address}_{qa_.name}_{qa_.decimals}_'
            f'{hash_id(partial_id)}',
        )

    @property
    def link(self) -> str:
        return self.tx_hash

    @property
    def pair(self) -> str:
        return f'{self.base_asset.symbol}_{self.quote_asset.symbol}'

    def serialize(self) -> Dict[str, Any]:
        """Serialize the trade into a dict matching Trade serialization from
        `data_structures.py` and adding: address, base_asset, quote_asset.
        """
        unk_asset_keys = ('ethereum_address', 'name', 'symbol')
        serialized_base_asset = (
            self.base_asset.serialize()
            if isinstance(self.base_asset, EthereumToken)
            else self.base_asset.serialize_as_dict(keys=unk_asset_keys)
        )
        serialized_quote_asset = (
            self.quote_asset.serialize()
            if isinstance(self.quote_asset, EthereumToken)
            else self.quote_asset.serialize_as_dict(keys=unk_asset_keys)
        )
        return {
            'timestamp': self.timestamp,
            'location': str(self.location),
            'pair': self.pair,
            'trade_type': str(self.trade_type),
            'amount': str(self.amount),
            'rate': str(self.rate),
            'fee': str(self.fee),
            'fee_currency': str(self.fee_currency),
            'link': self.link,
            'notes': self.notes,
            # Added trade attributes
            'address': self.address,
            'base_asset': serialized_base_asset,
            'quote_asset': serialized_quote_asset,
        }


AddressTrades = Dict[ChecksumEthAddress, List[AMMTrade]]
DDAddressTrades = DefaultDict[ChecksumEthAddress, List[AMMTrade]]
ProtocolHistory = Dict[str, Union[AddressTrades]]
