from collections.abc import Callable, Sequence
from enum import Enum, auto
from typing import Any, NamedTuple

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_int,
    deserialize_timestamp,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import BTCAddress, Timestamp
from rotkehlchen.utils.misc import satoshis_to_btc


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
    def deserialize_from_blockcypher(
            cls,
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        return BtcTxIO(
            value=satoshis_to_btc(
                data.get('value', 0) if direction == BtcTxIODirection.OUTPUT
                else data.get('output_value', 0),
            ),
            script=bytes.fromhex(script) if (script := data.get('script')) is not None else None,
            address=addresses[0] if (addresses := data['addresses']) is not None else None,
            direction=direction,
        )

    @classmethod
    def deserialize_from_blockchain_info(
            cls,
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        return BtcTxIO(
            value=satoshis_to_btc(data['value']),
            script=bytes.fromhex(data['script']),
            address=data.get('addr'),
            direction=direction,
        )

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

    @classmethod
    def deserialize_from_blockcypher(cls, data: dict[str, Any]) -> 'BitcoinTx':
        return cls(
            tx_id=data['hash'],
            timestamp=deserialize_timestamp_from_date(
                date=data['confirmed'],
                formatstr='iso8601',
                location='blockcypher bitcoin tx',
            ),
            block_height=deserialize_int(data['block_height']),
            fee=satoshis_to_btc(data['fees']),
            inputs=BtcTxIO.deserialize_list(
                data_list=data['inputs'],
                direction=BtcTxIODirection.INPUT,
                deserialize_fn=BtcTxIO.deserialize_from_blockcypher,
            ),
            outputs=BtcTxIO.deserialize_list(
                data_list=data['outputs'],
                direction=BtcTxIODirection.OUTPUT,
                deserialize_fn=BtcTxIO.deserialize_from_blockcypher,
            ),
        )

    @classmethod
    def deserialize_from_blockchain_info(cls, data: dict[str, Any]) -> 'BitcoinTx':
        inputs = [vin['prev_out'] for vin in data['inputs']]
        outputs = data['out']
        multi_io = False
        if (
            (vin_sz := data['vin_sz']) > 1 and
            (vout_sz := data['vout_sz']) > 1 and
            (len(inputs) != vin_sz or len(outputs) != vout_sz)
        ):
            # This api omits some TxIOs if they don't directly affect the addresses queried.
            # Set multi_io to ensure proper many-to-many decoding if some TxIOs are missing.
            multi_io = True

        return cls(
            tx_id=data['hash'],
            timestamp=deserialize_timestamp(data['time']),
            block_height=deserialize_int(data['block_height']),
            fee=satoshis_to_btc(data['fee']),
            inputs=BtcTxIO.deserialize_list(
                data_list=inputs,
                direction=BtcTxIODirection.INPUT,
                deserialize_fn=BtcTxIO.deserialize_from_blockchain_info,
            ),
            outputs=BtcTxIO.deserialize_list(
                data_list=outputs,
                direction=BtcTxIODirection.OUTPUT,
                deserialize_fn=BtcTxIO.deserialize_from_blockchain_info,
            ),
            multi_io=multi_io,
        )


def string_to_btc_address(value: str) -> BTCAddress:
    """Convert a string to a bitcoin address without any checks. Used only for typing."""
    return BTCAddress(value)
