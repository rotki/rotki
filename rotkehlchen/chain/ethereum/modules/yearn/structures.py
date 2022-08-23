import dataclasses
from typing import Any, Dict, Literal, NamedTuple, Optional, Tuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.ethereum import EthereumContract
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import (
    deserialize_optional_to_fval,
    deserialize_timestamp,
)
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp, make_evm_tx_hash

YEARN_EVENT_DB_TUPLE = Tuple[
    ChecksumEvmAddress,
    Literal['deposit', 'withdraw'],  # event_type
    str,  # from_asset identifier
    str,  # from_value amount
    str,  # from value usd_value
    str,  # to_asset idientifier
    str,  # to_value amount
    str,  # to value usd_value
    Optional[str],  # pnl amount
    Optional[str],  # pnl usd value
    str,  # block number
    str,  # str of timestamp
    bytes,  # tx hash
    int,  # log index
    int,  # version
]


@dataclasses.dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class YearnVaultEvent:
    event_type: Literal['deposit', 'withdraw']
    block_number: int
    timestamp: Timestamp
    from_asset: Asset
    from_value: Balance
    to_asset: Asset
    to_value: Balance
    realized_pnl: Optional[Balance]
    tx_hash: EVMTxHash
    log_index: int
    version: int

    def serialize(self) -> Dict[str, Any]:
        # Would have been nice to have a customizable asdict() for dataclasses
        # This way we could have avoided manual work with the Asset object serialization
        return {
            'event_type': self.event_type,
            'block_number': self.block_number,
            'timestamp': self.timestamp,
            'from_asset': self.from_asset.serialize(),
            'from_value': self.from_value.serialize(),
            'to_asset': self.to_asset.serialize(),
            'to_value': self.to_value.serialize(),
            'realized_pnl': self.realized_pnl.serialize() if self.realized_pnl else None,
            'tx_hash': self.tx_hash.hex(),
            'log_index': self.log_index,
        }

    def serialize_for_db(self, address: ChecksumEvmAddress) -> YEARN_EVENT_DB_TUPLE:
        pnl_amount = None
        pnl_usd_value = None
        if self.realized_pnl:
            pnl_amount = str(self.realized_pnl.amount)
            pnl_usd_value = str(self.realized_pnl.usd_value)
        vault_version = self.version
        return (
            address,
            self.event_type,
            self.from_asset.identifier,
            str(self.from_value.amount),
            str(self.from_value.usd_value),
            self.to_asset.identifier,
            str(self.to_value.amount),
            str(self.to_value.usd_value),
            pnl_amount,
            pnl_usd_value,
            str(self.block_number),
            str(self.timestamp),
            self.tx_hash,
            self.log_index,
            vault_version,
        )

    @classmethod
    def deserialize_from_db(cls, result: YEARN_EVENT_DB_TUPLE) -> 'YearnVaultEvent':
        """
        Turns a tuple read from the DB into an appropriate YearnVaultEvent
        May raise a DeserializationError if there is an issue with information in
        the database
        """
        location = 'deserialize yearn vault event from db'
        realized_pnl = None
        if result[8] is not None and result[9] is not None:
            pnl_amount = deserialize_optional_to_fval(
                value=result[8],
                name='pnl_amount',
                location=location,
            )
            pnl_usd_value = deserialize_optional_to_fval(
                value=result[9],
                name='pnl_usd_value',
                location=location,
            )
            realized_pnl = Balance(amount=pnl_amount, usd_value=pnl_usd_value)

        from_value_amount = deserialize_optional_to_fval(
            value=result[3],
            name='from_value_amount',
            location=location,
        )
        from_value_usd_value = deserialize_optional_to_fval(
            result[4],
            name='from_value_usd_value',
            location=location,
        )
        to_value_amount = deserialize_optional_to_fval(
            value=result[6],
            name='to_value_amount',
            location=location,
        )
        to_value_usd_value = deserialize_optional_to_fval(
            value=result[7],
            name='to_value_usd_value',
            location=location,
        )
        try:
            block_number = int(result[10])
        except ValueError as e:
            raise DeserializationError(
                f'Failed to deserialize block number {result[10]} in yearn vault event: {str(e)}',
            ) from e
        from_asset = Asset(result[2])
        to_asset = Asset(result[5])
        return cls(
            event_type=result[1],
            from_asset=from_asset,
            from_value=Balance(amount=from_value_amount, usd_value=from_value_usd_value),
            to_asset=to_asset,
            to_value=Balance(amount=to_value_amount, usd_value=to_value_usd_value),
            realized_pnl=realized_pnl,
            block_number=block_number,
            timestamp=deserialize_timestamp(result[11]),
            tx_hash=make_evm_tx_hash(result[12]),
            log_index=result[13],
            version=result[14],
        )

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return f'Yearn vault {self.event_type}'


class YearnVault(NamedTuple):
    name: str
    contract: EthereumContract
    underlying_token: EvmToken
    token: EvmToken
