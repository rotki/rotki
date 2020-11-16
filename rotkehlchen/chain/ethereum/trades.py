from typing import Any, Dict, NamedTuple, Tuple, Union

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import FakeAsset, UnknownEthereumToken
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
    TradeType,
)

# Quick lookup for AMMTrade locations
AMMTradeLocations = {Location.UNISWAP}
AMMTradeDBTuple = (
    Tuple[
        str,  # tx_hash
        int,  # log_index
        str,  # address
        int,  # timestamp
        str,  # location
        str,  # type
        int,  # is_base_asset_unknown
        str,  # base_asset_address
        str,  # base_asset_symbol
        str,  # base_asset_name
        int,  # base_asset_decimals
        int,  # is_quote_asset_unknown
        str,  # quote_asset_address
        str,  # quote_asset_symbol
        str,  # quote_asset_name
        int,  # quote_asset_decimals
        str,  # amount
        str,  # rate
        str,  # fee
        str,  # notes
    ]
)


class AMMTrade(NamedTuple):
    """This class aims for a better trades support than the current Trade class
    in AMMs protocols.
    """
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    from_address: ChecksumEthAddress
    to_address: ChecksumEthAddress
    timestamp: Timestamp
    location: Location
    trade_type: TradeType
    base_asset: Union[EthereumToken, UnknownEthereumToken]
    quote_asset: Union[EthereumToken, UnknownEthereumToken]
    amount: AssetAmount
    rate: Price
    fee: Fee
    notes: str = ''

    @classmethod
    def deserialize_from_db(
            cls,
            trade_tuple: AMMTradeDBTuple,
    ) -> 'AMMTrade':
        """Turns a tuple read from DB into an appropriate Trade.

        May raise a DeserializationError if something is wrong with the DB data

        Trade_tuple index - Schema columns
        ----------------------------------
        0 - tx_hash
        1 - log_index
        2 - address
        3 - from_address
        4 - to_address
        5 - timestamp
        6 - location
        7 - type
        8 - is_base_asset_unknown
        9 - base_asset_address
        10 - base_asset_symbol
        11 - base_asset_name
        12 - base_asset_decimals
        13 - is_quote_asset_unknown
        14 - quote_asset_address
        15 - quote_asset_symbol
        16 - quote_asset_name
        17 - quote_asset_decimals
        18 - amount
        19 - rate
        20 - fee
        21 - notes
        """
        address = deserialize_ethereum_address(trade_tuple[2])
        from_address = deserialize_ethereum_address(trade_tuple[3])
        to_address = deserialize_ethereum_address(trade_tuple[4])
        is_base_asset_unknown = trade_tuple[8]
        is_quote_asset_unknown = trade_tuple[13]

        base_asset: Union[EthereumToken, UnknownEthereumToken]
        quote_asset: Union[EthereumToken, UnknownEthereumToken]
        if is_base_asset_unknown:
            base_asset = deserialize_unknown_ethereum_token_from_db(
                ethereum_address=trade_tuple[9],
                symbol=trade_tuple[10],
                name=trade_tuple[11],
                decimals=trade_tuple[12],
            )
        else:
            base_asset = deserialize_ethereum_token_from_db(identifier=trade_tuple[10])

        if is_quote_asset_unknown:
            quote_asset = deserialize_unknown_ethereum_token_from_db(
                ethereum_address=trade_tuple[14],
                symbol=trade_tuple[15],
                name=trade_tuple[16],
                decimals=trade_tuple[17],
            )
        else:
            quote_asset = deserialize_ethereum_token_from_db(identifier=trade_tuple[15])

        return cls(
            tx_hash=trade_tuple[0],
            log_index=trade_tuple[1],
            address=address,
            from_address=from_address,
            to_address=to_address,
            timestamp=deserialize_timestamp(trade_tuple[5]),
            location=deserialize_location_from_db(trade_tuple[6]),
            trade_type=deserialize_trade_type_from_db(trade_tuple[7]),
            base_asset=base_asset,
            quote_asset=quote_asset,
            amount=deserialize_asset_amount(trade_tuple[18]),
            rate=deserialize_price(trade_tuple[19]),
            fee=deserialize_fee(trade_tuple[20]),
            notes=trade_tuple[21],
        )

    @property
    def fee_currency(self) -> FakeAsset:
        fee_asset = (
            self.base_asset
            if self.trade_type == TradeType.SELL
            else self.quote_asset
        )
        return FakeAsset(identifier=fee_asset.symbol)

    @property
    def identifier(self) -> str:
        return f'{self.tx_hash}-{self.log_index}'

    @property
    def link(self) -> str:
        return self.tx_hash

    @property
    def pair(self) -> str:
        return f'{self.base_asset.symbol}_{self.quote_asset.symbol}'

    @property
    def trade_id(self) -> str:
        return self.identifier

    def serialize(self) -> Dict[str, Any]:
        """Serialize the trade into a dict matching Trade serialization from
        `data_structures.py` and adding: address, base_asset, quote_asset,
        from_address and to_address
        """
        unknown_asset_keys = ('ethereum_address', 'name', 'symbol')
        serialized_base_asset = (
            self.base_asset.serialize()
            if isinstance(self.base_asset, EthereumToken)
            else self.base_asset.serialize_as_dict(keys=unknown_asset_keys)
        )
        serialized_quote_asset = (
            self.quote_asset.serialize()
            if isinstance(self.quote_asset, EthereumToken)
            else self.quote_asset.serialize_as_dict(keys=unknown_asset_keys)
        )
        return {
            # Shared attributes with Trade
            'trade_id': self.trade_id,  # PK
            'timestamp': self.timestamp,
            'location': str(self.location),
            'pair': self.pair,
            'trade_type': str(self.trade_type),
            'amount': str(self.amount),
            'rate': str(self.rate),
            'fee': str(self.fee),
            'fee_currency': self.fee_currency.identifier,
            'link': self.link,
            'notes': self.notes,
            # AMMTrade attributes
            'address': self.address,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'base_asset': serialized_base_asset,
            'quote_asset': serialized_quote_asset,
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
        }

    def to_db_tuple(self) -> AMMTradeDBTuple:
        is_base_asset_unknown = (
            1 if isinstance(self.base_asset, UnknownEthereumToken) else 0
        )
        is_quote_asset_unknown = (
            1 if isinstance(self.quote_asset, UnknownEthereumToken) else 0
        )
        db_tuple = (
            self.tx_hash,
            self.log_index,
            str(self.address),
            str(self.from_address),
            str(self.to_address),
            int(self.timestamp),
            self.location.serialize_for_db(),
            self.trade_type.serialize_for_db(),
            is_base_asset_unknown,
            str(self.base_asset.ethereum_address),
            str(self.base_asset.symbol),
            str(self.base_asset.name),
            self.base_asset.decimals,
            is_quote_asset_unknown,
            str(self.quote_asset.ethereum_address),
            str(self.quote_asset.symbol),
            str(self.quote_asset.name),
            self.quote_asset.decimals,
            str(self.amount),
            str(self.rate),
            str(self.fee),
            self.notes,
        )
        return db_tuple  # type: ignore
