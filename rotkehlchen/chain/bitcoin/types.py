from collections.abc import Callable, Sequence
from enum import Enum, auto
from typing import Any, NamedTuple

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.types import BTCAddress, Timestamp


class BtcQueryAction(Enum):
    BALANCES = auto()
    HAS_TRANSACTIONS = auto()
    TRANSACTIONS = auto()


class BtcTxIODirection(Enum):
    INPUT = auto()
    OUTPUT = auto()


class BtcApiCallback(NamedTuple):
    """Represents a callback for a bitcoin api."""
    name: str  # Used for logging
    balances_fn: Callable[[Sequence[BTCAddress]], dict[BTCAddress, FVal]] | None
    has_transactions_fn: Callable[[Sequence[BTCAddress]], dict[BTCAddress, tuple[bool, FVal]]] | None  # noqa: E501
    transactions_fn: Callable[[Sequence[BTCAddress], dict[str, Any]], tuple[int, list['BitcoinTx']]] | None  # noqa: E501


class BtcTxIO(NamedTuple):
    """Represents an individual input/output of a Bitcoin transaction."""
    value: FVal
    script: bytes | None  # optional since blockcypher omits the script for input TxIOs
    address: BTCAddress | None  # address may be missing for scripts such as op_return
    direction: BtcTxIODirection

    @classmethod
    def deserialize(
            cls,
            data: dict[str, Any],
            direction: BtcTxIODirection,
            deserialize_fn: Callable[[dict[str, Any], BtcTxIODirection], 'BtcTxIO'],
    ) -> 'BtcTxIO':
        try:
            return deserialize_fn(data, direction)
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e
        except ValueError as e:
            raise DeserializationError(f'Invalid hexadecimal script in TxIO {data}') from e

    @classmethod
    def deserialize_list(
            cls,
            data_list: list[dict[str, Any]],
            direction: BtcTxIODirection,
            deserialize_fn: Callable[[dict[str, Any], BtcTxIODirection], 'BtcTxIO'],
    ) -> list['BtcTxIO']:
        return [cls.deserialize(
            data=raw_tx_io,
            direction=direction,
            deserialize_fn=deserialize_fn,
        ) for raw_tx_io in data_list]


class BitcoinTx(NamedTuple):
    tx_id: str
    timestamp: Timestamp
    block_height: int
    fee: FVal
    inputs: list[BtcTxIO]
    outputs: list[BtcTxIO]
    multi_io: bool = False


def string_to_btc_address(value: str) -> BTCAddress:
    """Convert a string to a bitcoin address without any checks. Used only for typing."""
    return BTCAddress(value)
