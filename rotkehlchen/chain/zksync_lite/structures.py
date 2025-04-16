from dataclasses import dataclass

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EVMTxHash,
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
    SWAP = 7


ZKSyncLiteTransactionDBTuple = tuple[
    EVMTxHash,  # tx_hash
    str,    # type
    int,    # timestamp
    int,    # block number
    str,  # from_address
    str | None,  # to_address
    str,    # asset
    str,    # amount
    str | None,    # fee
]

ZKSyncLiteSwapDBTuple = tuple[
    int,  # tx_id
    str,  # from_asset
    str,  # from_amount
    str,  # to_asset
    str,  # to_amount
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=True, frozen=False)
class ZKSyncLiteSwapData:
    from_asset: Asset
    from_amount: FVal
    to_asset: Asset
    to_amount: FVal

    def serialize_for_db(self, identifier: int) -> ZKSyncLiteSwapDBTuple:
        return (
            identifier,
            self.from_asset.identifier,
            str(self.from_amount),
            self.to_asset.identifier,
            str(self.to_amount),
        )

    @classmethod
    def deserialize_from_db(
            cls,
            data: tuple[str, str, str, str],
    ) -> 'ZKSyncLiteSwapData':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            from_asset=Asset(data[0]),
            from_amount=deserialize_fval(data[1], 'from_amount', 'zksynclite swap'),
            to_asset=Asset(data[2]),
            to_amount=deserialize_fval(data[3], 'to_amount', 'zksynclite swap'),
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=True, frozen=False)
class ZKSyncLiteTransaction:
    tx_hash: EVMTxHash
    tx_type: ZKSyncLiteTXType
    timestamp: Timestamp
    block_number: int
    from_address: ChecksumEvmAddress
    to_address: ChecksumEvmAddress | None
    asset: Asset
    amount: FVal
    fee: FVal | None
    swap_data: ZKSyncLiteSwapData | None = None

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
            from_address=string_to_evm_address(data[4]),
            to_address=None if data[5] is None else string_to_evm_address(data[5]),
            asset=Asset(data[6]),
            amount=deserialize_fval(data[7], 'amount', 'zksync lite tx'),
            fee=deserialize_fval(data[8]) if data[8] is not None else None,
            swap_data=None,
        )
