from dataclasses import dataclass

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_fee
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EVMTxHash,
    Fee,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.mixins.enums import DBCharEnumMixIn


class ZKSyncLiteTXType(DBCharEnumMixIn):
    TRANSFER = 1
    DEPOSIT = 2
    WITHDRAW = 3
    CHANGEPUBKEY = 4  # we only use it for fee of changing public key
    FORCEDEXIT = 5  # we only use it for fee of exit.
    FULLEXIT = 6  # we only use it for fee of exit.


ZKSyncLiteTransactionDBTuple = tuple[
    EVMTxHash,  # tx_hash
    str,    # type
    int,    # timestamp
    int,    # block number
    str | None,  # from_address
    str | None,  # to_address
    str,    # asset
    str,    # amount
    str | None,    # fee
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=True, frozen=False)
class ZKSyncLiteTransaction:
    tx_hash: EVMTxHash
    tx_type: ZKSyncLiteTXType
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEvmAddress | None
    to_address: ChecksumEvmAddress | None
    asset: Asset
    amount: FVal
    fee: Fee | None

    def serialize_for_db(self) -> ZKSyncLiteTransactionDBTuple:
        return (
            self.tx_hash,
            self.tx_type.serialize_for_db(),
            self.timestamp,
            self.block_number,
            self.from_address,
            self.to_address,
            self.asset.identifier,
            str(self.amount),
            str(self.fee) if self.fee is not None else None,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            data: ZKSyncLiteTransactionDBTuple,
    ) -> 'ZKSyncLiteTransaction':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            tx_hash=deserialize_evm_tx_hash(data[0]),
            tx_type=ZKSyncLiteTXType.deserialize_from_db(data[1]),
            timestamp=Timestamp(data[2]),
            block_number=data[3],
            from_address=None if data[4] is None else string_to_evm_address(data[4]),
            to_address=None if data[5] is None else string_to_evm_address(data[5]),
            asset=Asset(data[6]),
            amount=deserialize_asset_amount(data[7]),
            fee=deserialize_fee(data[8]) if data[8] is not None else None,
        )
