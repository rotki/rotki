import dataclasses
from typing import Any, Dict, Literal, Optional, Tuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_optional_to_fval
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash, Timestamp, make_evm_tx_hash

AAVE_EVENT_TYPE = Literal['deposit', 'withdrawal', 'interest', 'borrow', 'repay', 'liquidation']
AAVE_EVENT_DB_TUPLE = Tuple[
    ChecksumEvmAddress,
    AAVE_EVENT_TYPE,
    int,  # block_number
    Timestamp,
    bytes,  # transaction hash
    int,  # log index
    str,  # asset1 identifier
    str,  # asset1 amount
    str,  # asset1 usd value
    Optional[str],  # asset2
    Optional[str],  # asset2 amount / borrow rate / fee amount
    Optional[str],  # asset2 usd value / borrow accrued interest rate / fee usd value
    Optional[str],  # borrow rate mode
]


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class AaveEvent:
    """An event of the Aave protocol"""
    event_type: AAVE_EVENT_TYPE
    # for events coming from Graph this is not retrievable
    # Because of this "TODO":
    # https://github.com/aave/aave-protocol/blob/f7ef52000af2964046857da7e5fe01894a51f2ab/thegraph/raw/schema.graphql#L144
    block_number: int
    timestamp: Timestamp
    tx_hash: EVMTxHash
    # only used to identify uniqueness. Does not really correspond to the real log
    # index for graph queries. Because of this "TODO":
    # https://github.com/aave/aave-protocol/blob/f7ef52000af2964046857da7e5fe01894a51f2ab/thegraph/raw/schema.graphql#L144
    log_index: int

    def serialize(self) -> Dict[str, Any]:
        data = dataclasses.asdict(self)
        data['tx_hash'] = self.tx_hash.hex()
        return data

    def to_db_tuple(self, address: ChecksumEvmAddress) -> Tuple[
        ChecksumEvmAddress,
        AAVE_EVENT_TYPE,
        int,
        Timestamp,
        EVMTxHash,
        int,
    ]:
        return (
            address,
            self.event_type,
            self.block_number,
            self.timestamp,
            self.tx_hash,
            self.log_index,
        )

    def __hash__(self) -> int:
        return hash(self.event_type.encode() + self.tx_hash + str(self.log_index).encode())

    def __eq__(self, other: Any) -> bool:
        return hash(self) == hash(other)

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return f'Aave {self.event_type} event'


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class AaveInterestEvent(AaveEvent):
    """A simple event of the Aave protocol. Deposit, withdrawal or interest"""
    asset: CryptoAsset
    value: Balance

    def serialize(self) -> Dict[str, Any]:
        result = super().serialize()
        result['asset'] = self.asset.identifier
        return result

    def to_db_tuple(self, address: ChecksumEvmAddress) -> AAVE_EVENT_DB_TUPLE:  # type: ignore
        base_tuple = super().to_db_tuple(address)
        return base_tuple + (
            self.asset.identifier,
            str(self.value.amount),
            str(self.value.usd_value),
            None,  # asset2
            None,  # asset2 amount / borrow rate / fee amount
            None,  # asset2 usd value / borrow accrued interest rate / fee usd value
            None,  # borrow rate mode
        )


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class AaveDepositWithdrawalEvent(AaveEvent):
    """A deposit or withdrawal in the aave protocol"""
    asset: CryptoAsset
    value: Balance
    atoken: EvmToken

    def serialize(self) -> Dict[str, Any]:
        result = super().serialize()
        result['asset'] = self.asset.identifier
        result['atoken'] = self.atoken.identifier
        return result

    def to_db_tuple(self, address: ChecksumEvmAddress) -> AAVE_EVENT_DB_TUPLE:  # type: ignore
        base_tuple = super().to_db_tuple(address)
        return base_tuple + (
            self.asset.identifier,
            str(self.value.amount),
            str(self.value.usd_value),
            str(self.atoken.identifier),  # asset2
            None,  # asset2 amount / borrow rate / fee amount
            None,  # asset2 usd value / borrow accrued interest rate / fee usd value
            None,  # borrow rate mode
        )


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class AaveBorrowEvent(AaveInterestEvent):
    """A borrow event of the Aave protocol"""
    borrow_rate_mode: Literal['stable', 'variable']
    borrow_rate: FVal
    accrued_borrow_interest: FVal

    def to_db_tuple(self, address: ChecksumEvmAddress) -> AAVE_EVENT_DB_TUPLE:  # type: ignore
        base_tuple = AaveEvent.to_db_tuple(self, address)
        return base_tuple + (
            self.asset.identifier,
            str(self.value.amount),
            str(self.value.usd_value),
            None,  # asset2
            str(self.borrow_rate),  # asset2 amount / borrow rate / fee amount
            str(self.accrued_borrow_interest),  # asset2 usd value / borrow accrued interest rate / fee usd value  # noqa: E501
            self.borrow_rate_mode,  # borrow rate mode
        )


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class AaveRepayEvent(AaveInterestEvent):
    """A repay event of the Aave protocol"""
    fee: Balance

    def to_db_tuple(self, address: ChecksumEvmAddress) -> AAVE_EVENT_DB_TUPLE:  # type: ignore
        base_tuple = AaveEvent.to_db_tuple(self, address)
        return base_tuple + (
            self.asset.identifier,
            str(self.value.amount),
            str(self.value.usd_value),
            None,  # asset2
            str(self.fee.amount),  # asset2 amount / borrow rate / fee amount
            str(self.fee.usd_value),  # asset2 usd value / borrow accrued interest rate / fee usd value  # noqa: E501
            None,  # borrow rate mode
        )


@dataclasses.dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class AaveLiquidationEvent(AaveEvent):
    """An aave liquidation event. You gain the principal and lose the collateral."""
    collateral_asset: CryptoAsset
    collateral_balance: Balance
    principal_asset: CryptoAsset
    principal_balance: Balance

    def serialize(self) -> Dict[str, Any]:
        result = super().serialize()
        result['collateral_asset'] = self.collateral_asset.identifier
        result['principal_asset'] = self.principal_asset.identifier
        return result

    def to_db_tuple(self, address: ChecksumEvmAddress) -> AAVE_EVENT_DB_TUPLE:  # type: ignore
        base_tuple = super().to_db_tuple(address)
        return base_tuple + (
            self.collateral_asset.identifier,
            str(self.collateral_balance.amount),
            str(self.collateral_balance.usd_value),
            self.principal_asset.identifier,  # asset2
            str(self.principal_balance.amount),  # asset2 amount / borrow rate / fee amount
            str(self.principal_balance.usd_value),  # asset2 usd value / borrow accrued interest rate / fee usd value  # noqa: E501
            None,  # borrow rate mode
        )


def aave_event_from_db(event_tuple: AAVE_EVENT_DB_TUPLE) -> AaveEvent:
    """Turns a tuple read from the DB into an appropriate AaveEvent

    May raise a DeserializationError if something is wrong with the DB data
    """
    event_type = event_tuple[1]
    block_number = event_tuple[2]
    timestamp = Timestamp(event_tuple[3])
    tx_hash = make_evm_tx_hash(event_tuple[4])
    log_index = event_tuple[5]
    asset2 = None
    if event_tuple[9] is not None:
        try:
            asset2 = CryptoAsset(event_tuple[9])
        except (UnknownAsset, WrongAssetType) as e:
            raise DeserializationError(
                f'Unknown asset {event_tuple[6]} encountered during deserialization '
                f'of Aave event from DB for asset2',
            ) from e

    try:
        asset1 = CryptoAsset(event_tuple[6])
    except UnknownAsset as e:
        raise DeserializationError(
            f'Unknown asset {event_tuple[6]} encountered during deserialization '
            f'of Aave event from DB for asset1',
        ) from e
    asset1_amount = FVal(event_tuple[7])
    asset1_usd_value = FVal(event_tuple[8])

    if event_type in ('deposit', 'withdrawal'):
        return AaveDepositWithdrawalEvent(
            event_type=event_type,
            block_number=block_number,
            timestamp=timestamp,
            tx_hash=tx_hash,
            log_index=log_index,
            asset=asset1,
            atoken=EvmToken(asset2.identifier),  # type: ignore # should be a token
            value=Balance(amount=asset1_amount, usd_value=asset1_usd_value),
        )
    if event_type == 'interest':
        return AaveInterestEvent(
            event_type=event_type,
            block_number=block_number,
            timestamp=timestamp,
            tx_hash=tx_hash,
            log_index=log_index,
            asset=asset1,
            value=Balance(amount=asset1_amount, usd_value=asset1_usd_value),
        )
    if event_type == 'borrow':
        if event_tuple[12] not in ('stable', 'variable'):
            raise DeserializationError(
                f'Invalid borrow rate mode encountered in the DB: {event_tuple[12]}',
            )
        borrow_rate_mode: Literal['stable', 'variable'] = event_tuple[12]  # type: ignore
        borrow_rate = deserialize_optional_to_fval(
            value=event_tuple[10],
            name='borrow_rate',
            location='reading aave borrow event from DB',
        )
        accrued_borrow_interest = deserialize_optional_to_fval(
            value=event_tuple[11],
            name='accrued_borrow_interest',
            location='reading aave borrow event from DB',
        )
        return AaveBorrowEvent(
            event_type=event_type,
            block_number=block_number,
            timestamp=timestamp,
            tx_hash=tx_hash,
            log_index=log_index,
            asset=asset1,
            value=Balance(amount=asset1_amount, usd_value=asset1_usd_value),
            borrow_rate_mode=borrow_rate_mode,
            borrow_rate=borrow_rate,
            accrued_borrow_interest=accrued_borrow_interest,
        )
    if event_type == 'repay':
        fee_amount = deserialize_optional_to_fval(
            value=event_tuple[10],
            name='fee_amount',
            location='reading aave repay event from DB',
        )
        fee_usd_value = deserialize_optional_to_fval(
            value=event_tuple[11],
            name='fee_usd_value',
            location='reading aave repay event from DB',
        )
        return AaveRepayEvent(
            event_type=event_type,
            block_number=block_number,
            timestamp=timestamp,
            tx_hash=tx_hash,
            log_index=log_index,
            asset=asset1,
            value=Balance(amount=asset1_amount, usd_value=asset1_usd_value),
            fee=Balance(amount=fee_amount, usd_value=fee_usd_value),
        )
    if event_type == 'liquidation':
        if asset2 is None:
            raise DeserializationError(
                'Did not find asset2 in an aave liquidation event fom the DB.',
            )
        principal_amount = deserialize_optional_to_fval(
            value=event_tuple[10],
            name='principal_amount',
            location='reading aave liquidation event from DB',
        )
        principal_usd_value = deserialize_optional_to_fval(
            value=event_tuple[11],
            name='principal_usd_value',
            location='reading aave liquidation event from DB',
        )
        return AaveLiquidationEvent(
            event_type=event_type,
            block_number=block_number,
            timestamp=timestamp,
            tx_hash=tx_hash,
            log_index=log_index,
            collateral_asset=asset1,
            collateral_balance=Balance(amount=asset1_amount, usd_value=asset1_usd_value),
            principal_asset=asset2,
            principal_balance=Balance(
                amount=principal_amount,
                usd_value=principal_usd_value,
            ),
        )
    # else
    raise DeserializationError(
        f'Unknown event type {event_type} encountered during '
        f'deserialization of Aave event from DB',
    )
