import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, NamedTuple

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import BTCAddress, TimestampMS
from rotkehlchen.utils.misc import satoshis_to_btc, ts_sec_to_ms

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BtcScriptType(Enum):
    """Represents the type of a Bitcoin script.
    See https://learnmeabitcoin.com/technical/script/#standard-scripts
    """
    # Pay-to-Public-Key (Legacy) - lock output to public key - the simpler version of p2pkh
    P2PK = auto()
    # Pay-to-Public-Key-Hash (Legacy) - lock output to public key hash (send somebody btc)
    P2PKH = auto()
    # Pay-to-MultiSig (Legacy) - lock btc to multiple public keys
    P2MS = auto()
    # Pay-to-Script-Hash (Legacy) - lock btc to the hash of a script
    P2SH = auto()
    # lock data in the transaction - Used to store data on the blockchain
    OP_RETURN = auto()
    # Pay-to-Witness-Public-Key-Hash - segwit lock to public key hash (similar to p2pkh)
    P2WPKH = auto()
    # Pay-to-Witness-Script-Hash - seqwit lock to hash of script (similar to p2wsh)
    P2WSH = auto()
    # Pay-to-Taproot - lock output to a public key and multiple optional custom locking scripts
    P2TR = auto()
    # Other non-standard script
    CUSTOM = auto()


API_SCRIPT_TYPE_MAPPING = {
    'p2pk': BtcScriptType.P2PK,
    'p2pkh': BtcScriptType.P2PKH,
    'p2ms': BtcScriptType.P2MS,
    'p2sh': BtcScriptType.P2SH,
    'op_return': BtcScriptType.OP_RETURN,
    'v0_p2wpkh': BtcScriptType.P2WPKH,
    'v0_p2wsh': BtcScriptType.P2WSH,
    'v1_p2tr': BtcScriptType.P2TR,
}


class BtcTxIO(NamedTuple):
    """Represents an individual input/output of a Bitcoin transaction."""
    value: FVal
    pubkey: str
    type: BtcScriptType
    raw_script: str
    address: BTCAddress | None
    is_out: bool

    @classmethod
    def deserialize(cls, data: dict[str, Any], is_out: bool) -> 'BtcTxIO':
        try:
            if (raw_type := data.get('scriptpubkey_type')) is None or raw_type not in API_SCRIPT_TYPE_MAPPING:
                log.warning(f'Encountered unknown bitcoin script type {raw_type} in TxInOut {data}')
                script_type = BtcScriptType.CUSTOM
            else:
                script_type = API_SCRIPT_TYPE_MAPPING[raw_type]

            return BtcTxIO(
                value=satoshis_to_btc(data['value']),
                pubkey=data['scriptpubkey'],
                type=script_type,
                raw_script=data['scriptpubkey_asm'],
                address=data.get('scriptpubkey_address'),
                is_out=is_out,
            )
        except KeyError as e:
            raise DeserializationError(f'Failed to deserialize TxInOut due to missing key {e!s}') from e

    @classmethod
    def deserialize_list(cls, data_list: list[dict[str, Any]], is_out: bool) -> list['BtcTxIO']:
        return [cls.deserialize(data=raw_tx_io, is_out=is_out) for raw_tx_io in data_list]


class BitcoinTx(NamedTuple):
    tx_id: str
    timestamp: TimestampMS
    fee: FVal
    inputs: list[BtcTxIO]
    outputs: list[BtcTxIO]

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'BitcoinTx | None':
        try:
            return BitcoinTx(
                tx_id=data['txid'],
                timestamp=ts_sec_to_ms(deserialize_timestamp(data['status']['block_time'])),
                fee=satoshis_to_btc(data['fee']),
                inputs=BtcTxIO.deserialize_list(
                    data_list=[vin['prevout'] for vin in data['vin']],
                    is_out=False,
                ),
                outputs=BtcTxIO.deserialize_list(
                    data_list=data['vout'],
                    is_out=True,
                ),
            )
        except (DeserializationError, KeyError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            log.error(f'Failed to deserialize bitcoin transaction {data} due to {msg}')
            return None

def string_to_btc_address(value: str) -> BTCAddress:
    """This is a conversion without any checks of a string to bitcoin address

    Is only used for typing.
    """
    return BTCAddress(value)
