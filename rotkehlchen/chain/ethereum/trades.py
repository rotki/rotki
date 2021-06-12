from typing import Any, Dict, List, NamedTuple, Tuple

from typing_extensions import Literal

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_address,
    deserialize_ethereum_token_from_db,
    deserialize_timestamp,
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
        str,  # token0_identifier
        str,  # token1_identifier
        str,  # amount0_in
        str,  # amount1_in
        str,  # amount0_out
        str,  # amount1_out
    ]
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
    token0: EthereumToken
    token1: EthereumToken
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
        7 - token0_identifier
        8 - token1_identifier
        9 - amount0_in
        10 - amount1_in
        11 - amount0_out
        12 - amount1_out
        """
        address = deserialize_ethereum_address(trade_tuple[2])
        from_address = deserialize_ethereum_address(trade_tuple[3])
        to_address = deserialize_ethereum_address(trade_tuple[4])

        token0 = deserialize_ethereum_token_from_db(identifier=trade_tuple[7])
        token1 = deserialize_ethereum_token_from_db(identifier=trade_tuple[8])

        return cls(
            tx_hash=trade_tuple[0],
            log_index=trade_tuple[1],
            address=address,
            from_address=from_address,
            to_address=to_address,
            timestamp=deserialize_timestamp(trade_tuple[5]),
            location=Location.deserialize_from_db(trade_tuple[6]),
            token0=token0,
            token1=token1,
            amount0_in=deserialize_asset_amount(trade_tuple[9]),
            amount1_in=deserialize_asset_amount(trade_tuple[10]),
            amount0_out=deserialize_asset_amount(trade_tuple[11]),
            amount1_out=deserialize_asset_amount(trade_tuple[12]),
        )

    def serialize(self) -> Dict[str, Any]:
        """Serialize the swap into the format seen in the frontend"""
        return {
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'token0': self.token0.serialize(),
            'token1': self.token1.serialize(),
            'amount0_in': str(self.amount0_in),
            'amount1_in': str(self.amount1_in),
            'amount0_out': str(self.amount0_out),
            'amount1_out': str(self.amount1_out),
        }

    def to_db_tuple(self) -> AMMSwapDBTuple:
        db_tuple = (
            self.tx_hash,
            self.log_index,
            str(self.address),
            str(self.from_address),
            str(self.to_address),
            int(self.timestamp),
            self.location.serialize_for_db(),
            self.token0.identifier,
            self.token1.identifier,
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
    base_asset: EthereumToken
    quote_asset: EthereumToken
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
        return {
            # Shared attributes with Trade
            'trade_id': self.trade_id,  # PK
            'timestamp': self.timestamp,
            'location': str(self.location),
            'trade_type': str(self.trade_type),
            'amount': str(self.amount),
            'rate': str(self.rate),
            'fee': '0',  # Don't bother with a fee at the moment -- too complicated
            'fee_currency': self.quote_asset.identifier,
            # AMMTrade attributes
            'address': self.address,
            'base_asset': self.base_asset.identifier,
            'quote_asset': self.quote_asset.identifier,
            'tx_hash': self.tx_hash,
            'swaps': [x.serialize() for x in self.swaps],
        }
