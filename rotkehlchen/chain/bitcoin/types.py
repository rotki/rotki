from enum import Enum, auto
from typing import Any, NamedTuple

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import BTCAddress, TimestampMS
from rotkehlchen.utils.misc import satoshis_to_btc, ts_sec_to_ms


class BtcQueryAction(Enum):
    BALANCES = auto()
    HAS_TRANSACTIONS = auto()
    TRANSACTIONS = auto()


class BtcScriptType(Enum):
    """Represents the Bitcoin script type. There are more, but only defining here the ones that
    need special treatment. See https://learnmeabitcoin.com/technical/script/#standard-scripts
    """
    P2PK = auto()  # Pay-to-Public-Key (Legacy) - Public key needs to be converted to normal btc address.  # noqa: E501
    OP_RETURN = auto()  # Stores data onchain. Not a value transfer.
    OTHER = auto()


API_SCRIPT_TYPE_MAPPING = {
    'p2pk': BtcScriptType.P2PK,
    'op_return': BtcScriptType.OP_RETURN,
}


class BtcTxIODirection(Enum):
    INPUT = auto()
    OUTPUT = auto()


class BtcTxIO(NamedTuple):
    """Represents an individual input/output of a Bitcoin transaction."""
    value: FVal
    pubkey: str
    type: BtcScriptType
    raw_script: str
    address: BTCAddress | None
    direction: BtcTxIODirection

    @classmethod
    def deserialize(cls, data: dict[str, Any], direction: BtcTxIODirection) -> 'BtcTxIO':
        try:
            return BtcTxIO(
                value=satoshis_to_btc(data['value']),
                pubkey=data['scriptpubkey'],
                type=API_SCRIPT_TYPE_MAPPING.get(data.get('scriptpubkey_type', ''), BtcScriptType.OTHER),  # noqa: E501
                raw_script=data['scriptpubkey_asm'],
                address=data.get('scriptpubkey_address'),
                direction=direction,
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e

    @classmethod
    def deserialize_list(
            cls,
            data_list: list[dict[str, Any]],
            direction: BtcTxIODirection,
    ) -> list['BtcTxIO']:
        return [cls.deserialize(data=raw_tx_io, direction=direction) for raw_tx_io in data_list]


class BitcoinTx(NamedTuple):
    tx_id: str
    timestamp: TimestampMS
    fee: FVal
    inputs: list[BtcTxIO]
    outputs: list[BtcTxIO]

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'BitcoinTx':
        try:
            return cls(
                tx_id=data['txid'],
                timestamp=ts_sec_to_ms(deserialize_timestamp(data['status']['block_time'])),
                fee=satoshis_to_btc(data['fee']),
                inputs=BtcTxIO.deserialize_list(
                    data_list=[vin['prevout'] for vin in data['vin']],
                    direction=BtcTxIODirection.INPUT,
                ),
                outputs=BtcTxIO.deserialize_list(
                    data_list=data['vout'],
                    direction=BtcTxIODirection.OUTPUT,
                ),
            )
        except KeyError as e:
            raise DeserializationError(f'Missing key {e!s}') from e


def string_to_btc_address(value: str) -> BTCAddress:
    """Convert a string to a bitcoin address without any checks. Used only for typing."""
    return BTCAddress(value)
