from collections.abc import Callable
from enum import Enum, auto
from typing import Any, NamedTuple

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import BTCAddress, Timestamp
from rotkehlchen.utils.misc import satoshis_to_btc


class BtcQueryAction(Enum):
    BALANCES = auto()
    HAS_TRANSACTIONS = auto()
    TRANSACTIONS = auto()


class BtcTxIODirection(Enum):
    INPUT = auto()
    OUTPUT = auto()


class BtcTxIO(NamedTuple):
    """Represents an individual input/output of a Bitcoin transaction."""
    value: FVal
    script: bytes
    address: BTCAddress | None
    direction: BtcTxIODirection

    @classmethod
    def deserialize_from_blockstream_mempool(
            cls,
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        try:
            return BtcTxIO(
                value=satoshis_to_btc(data['value']),
                script=bytes.fromhex(data['scriptpubkey']),
                address=data.get('scriptpubkey_address'),
                direction=direction,
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    @classmethod
    def deserialize_from_blockchain_info(
            cls,
            data: dict[str, Any],
            direction: BtcTxIODirection,
    ) -> 'BtcTxIO':
        try:
            return BtcTxIO(
                value=satoshis_to_btc(data['value']),
                script=bytes.fromhex(data['script']),
                address=data.get('addr'),
                direction=direction,
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    @classmethod
    def deserialize_list(
            cls,
            data_list: list[dict[str, Any]],
            direction: BtcTxIODirection,
            deserialize_fn: Callable[[dict[str, Any], BtcTxIODirection], 'BtcTxIO'],
    ) -> list['BtcTxIO']:
        return [deserialize_fn(raw_tx_io, direction) for raw_tx_io in data_list]


class BitcoinTx(NamedTuple):
    tx_id: str
    timestamp: Timestamp
    fee: FVal
    inputs: list[BtcTxIO]
    outputs: list[BtcTxIO]

    @classmethod
    def deserialize_from_blockstream_mempool(cls, data: dict[str, Any]) -> 'BitcoinTx':
        try:
            return cls(
                tx_id=data['txid'],
                timestamp=deserialize_timestamp(data['status']['block_time']),
                fee=satoshis_to_btc(data['fee']),
                inputs=BtcTxIO.deserialize_list(
                    data_list=[vin['prevout'] for vin in data['vin']],
                    direction=BtcTxIODirection.INPUT,
                    deserialize_fn=BtcTxIO.deserialize_from_blockstream_mempool,
                ),
                outputs=BtcTxIO.deserialize_list(
                    data_list=data['vout'],
                    direction=BtcTxIODirection.OUTPUT,
                    deserialize_fn=BtcTxIO.deserialize_from_blockstream_mempool,
                ),
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    @classmethod
    def deserialize_from_blockchain_info(cls, data: dict[str, Any]) -> 'BitcoinTx':
        try:
            return cls(
                tx_id=data['hash'],
                timestamp=deserialize_timestamp(data['time']),
                fee=satoshis_to_btc(data['fee']),
                inputs=BtcTxIO.deserialize_list(
                    data_list=[vin['prev_out'] for vin in data['inputs']],
                    direction=BtcTxIODirection.INPUT,
                    deserialize_fn=BtcTxIO.deserialize_from_blockchain_info,
                ),
                outputs=BtcTxIO.deserialize_list(
                    data_list=data['out'],
                    direction=BtcTxIODirection.OUTPUT,
                    deserialize_fn=BtcTxIO.deserialize_from_blockchain_info,
                ),
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e


def string_to_btc_address(value: str) -> BTCAddress:
    """Convert a string to a bitcoin address without any checks. Used only for typing."""
    return BTCAddress(value)
