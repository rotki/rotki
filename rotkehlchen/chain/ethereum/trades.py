from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from typing_extensions import Literal

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UNKNOWN_TOKEN_KEYS, UnknownEthereumToken
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_address,
    deserialize_ethereum_token_from_db,
    deserialize_location_from_db,
    deserialize_timestamp,
    deserialize_unknown_ethereum_token_from_db,
)
from rotkehlchen.typing import (
    AssetAmount,
    ChecksumEthAddress,
    Fee,
    Location,
    Price,
    Timestamp,
    TradePair,
    TradeType,
)

# Quick lookup for AMMTrade locations
AMMTradeLocations = {Location.BALANCER, Location.UNISWAP}
AMMTRADE_LOCATION_NAMES = Literal['balancer', 'uniswap']
AMMSwapDBTuple = (
    Tuple[
        str,  # tx_hash
        int,  # log_index
        str,  # address
        str,  # from_address
        str,  # to_address
        int,  # timestamp
        str,  # location
        int,  # is_token0_unknown
        str,  # token0_address
        str,  # token0_symbol
        Optional[str],  # token0_name
        Optional[int],  # token0_decimals
        int,  # is_token1_unknown
        str,  # token1_address
        str,  # token1_symbol
        Optional[str],  # token1_name
        Optional[int],  # token1_decimals
        str,  # amount0_in
        str,  # amount1_in
        str,  # amount0_out
        str,  # amount1_out
    ]
)


def serialize_known_or_unknown_token(
        token: Union[EthereumToken, UnknownEthereumToken],
) -> Union[str, Dict[str, Any]]:
    return (
        token.serialize()
        if isinstance(token, EthereumToken)
        else token.serialize_as_dict(keys=UNKNOWN_TOKEN_KEYS)
    )


class AMMSwap(NamedTuple):
    """Represents a single AMM swap

    For now only catering to uniswap. We will see for more when we integrate them
    """
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    from_address: ChecksumEthAddress
    to_address: ChecksumEthAddress
    timestamp: Timestamp
    location: Location
    token0: Union[EthereumToken, UnknownEthereumToken]
    token1: Union[EthereumToken, UnknownEthereumToken]
    amount0_in: AssetAmount
    amount1_in: AssetAmount
    amount0_out: AssetAmount
    amount1_out: AssetAmount

    def __hash__(self) -> int:
        return hash(self.tx_hash + str(self.log_index))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)

    @classmethod
    def deserialize_from_db(
            cls,
            trade_tuple: AMMSwapDBTuple,
    ) -> 'AMMSwap':
        """Turns a tuple read from DB into an appropriate Swap.

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
        7 - is_token0_unknown
        8 - token0_address
        9 - token0_symbol
        10 - token0_name
        11 - token0_decimals
        12 - is_token1_unknown
        13 - token1_address
        14 - token1_symbol
        15 - token1_name
        16 - token1_decimals
        17 - amount0_in
        18 - amount1_in
        19 - amount0_out
        20 - amount1_out
        """
        address = deserialize_ethereum_address(trade_tuple[2])
        from_address = deserialize_ethereum_address(trade_tuple[3])
        to_address = deserialize_ethereum_address(trade_tuple[4])
        is_token0_unknown = trade_tuple[7]
        is_token1_unknown = trade_tuple[12]

        token0: Union[EthereumToken, UnknownEthereumToken]
        token1: Union[EthereumToken, UnknownEthereumToken]
        if is_token0_unknown:
            token0 = deserialize_unknown_ethereum_token_from_db(
                ethereum_address=trade_tuple[8],
                symbol=trade_tuple[9],
                name=trade_tuple[10],
                decimals=trade_tuple[11],
            )
        else:
            token0 = deserialize_ethereum_token_from_db(identifier=trade_tuple[9])

        if is_token1_unknown:
            token1 = deserialize_unknown_ethereum_token_from_db(
                ethereum_address=trade_tuple[13],
                symbol=trade_tuple[14],
                name=trade_tuple[15],
                decimals=trade_tuple[16],
            )
        else:
            token1 = deserialize_ethereum_token_from_db(identifier=trade_tuple[14])

        return cls(
            tx_hash=trade_tuple[0],
            log_index=trade_tuple[1],
            address=address,
            from_address=from_address,
            to_address=to_address,
            timestamp=deserialize_timestamp(trade_tuple[5]),
            location=deserialize_location_from_db(trade_tuple[6]),
            token0=token0,
            token1=token1,
            amount0_in=deserialize_asset_amount(trade_tuple[17]),
            amount1_in=deserialize_asset_amount(trade_tuple[18]),
            amount0_out=deserialize_asset_amount(trade_tuple[19]),
            amount1_out=deserialize_asset_amount(trade_tuple[20]),
        )

    def serialize(self) -> Dict[str, Any]:
        """Serialize the swap into the format seen in the frontend"""
        return {
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'token0': serialize_known_or_unknown_token(self.token0),
            'token1': serialize_known_or_unknown_token(self.token1),
            'amount0_in': str(self.amount0_in),
            'amount1_in': str(self.amount1_in),
            'amount0_out': str(self.amount0_out),
            'amount1_out': str(self.amount1_out),
        }

    def to_db_tuple(self) -> AMMSwapDBTuple:
        is_token0_unknown = (
            1 if isinstance(self.token0, UnknownEthereumToken) else 0
        )
        is_token1_unknown = (
            1 if isinstance(self.token1, UnknownEthereumToken) else 0
        )
        db_tuple = (
            self.tx_hash,
            self.log_index,
            str(self.address),
            str(self.from_address),
            str(self.to_address),
            int(self.timestamp),
            self.location.serialize_for_db(),
            is_token0_unknown,
            str(self.token0.ethereum_address),
            str(self.token0.symbol),
            self.token0.name,
            self.token0.decimals,
            is_token1_unknown,
            str(self.token1.ethereum_address),
            str(self.token1.symbol),
            self.token1.name,
            self.token1.decimals,
            str(self.amount0_in),
            str(self.amount1_in),
            str(self.amount0_out),
            str(self.amount1_out),
        )
        return db_tuple


class AMMTrade(NamedTuple):
    """This class aims for a better trades support than the current Trade class
    in AMMs protocols.
    """
    trade_type: TradeType
    base_asset: Union[EthereumToken, UnknownEthereumToken]
    quote_asset: Union[EthereumToken, UnknownEthereumToken]
    amount: AssetAmount
    rate: Price
    swaps: List[AMMSwap]
    # Since these trades are made up, we need an extra id for uniqueness at construction
    trade_index: int

    @property
    def tx_hash(self) -> str:
        return self.swaps[0].tx_hash

    @property
    def timestamp(self) -> Timestamp:
        return self.swaps[0].timestamp

    @property
    def location(self) -> Location:
        return self.swaps[0].location

    @property
    def address(self) -> ChecksumEthAddress:
        return self.swaps[0].address

    @property
    def identifier(self) -> str:
        """Since these trades are made up, uniqueness needs an extra id"""
        return f'{self.tx_hash}-{self.trade_index}'

    @property
    def pair(self) -> TradePair:
        return TradePair(f'{self.base_asset.symbol}_{self.quote_asset.symbol}')

    @property
    def trade_id(self) -> str:
        return self.identifier

    @property
    def fee_currency(self) -> EthereumToken:
        # always 0 DAI, super hacky -- just to satisfy the "Trade" interface for
        # use in accounting module. We need to fix these stuff ...
        return A_DAI

    @property
    def fee(self) -> Fee:
        return Fee(ZERO)

    def serialize(self) -> Dict[str, Any]:
        """Serialize the trade into a dict matching Trade serialization from
        `data_structures.py` and adding: address, base_asset, quote_asset,
        """
        fee_symbol = (
            self.quote_asset.identifier
            if isinstance(self.quote_asset, EthereumToken)
            else self.quote_asset.symbol
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
            'fee': '0',  # Don't bother with a fee at the moment -- too complicated
            'fee_currency': fee_symbol,
            # AMMTrade attributes
            'address': self.address,
            'base_asset': serialize_known_or_unknown_token(self.base_asset),
            'quote_asset': serialize_known_or_unknown_token(self.quote_asset),
            'tx_hash': self.tx_hash,
            'swaps': [x.serialize() for x in self.swaps],
        }
