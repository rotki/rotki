from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Self

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Location, Timestamp
from rotkehlchen.utils.mixins.enums import DBIntEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.assets.asset import Asset

    VALIDATOR_DETAILS_DB_TUPLE = tuple[int | None, Eth2PubKey, int, str, ChecksumEvmAddress | None, Timestamp | None, Timestamp | None, Timestamp | None]  # noqa: E501


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ValidatorID:
    index: int | None
    public_key: Eth2PubKey

    def __hash__(self) -> int:
        return hash(self.public_key)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ValidatorID) and self.public_key == other.public_key


ValidatorDailyStatsDBTuple = tuple[
    int,  # validator index
    int,  # timestamp
    str,  # pnl_amount
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ValidatorDailyStats(AccountingEventMixin):
    validator_index: int  # keeping the index here so it can be shown in accounting
    timestamp: Timestamp
    pnl: FVal = ZERO  # Value in ETH
    ownership_percentage: FVal = ONE  # customized by refresh_eth2_get_daily_stats

    def __str__(self) -> str:
        return f'ETH2 validator {self.validator_index} daily stats'

    @property
    def pnl_balance(self) -> Balance:
        try:
            usd_price = PriceHistorian().query_historical_price(
                from_asset=A_ETH,
                to_asset=A_USD,
                timestamp=self.timestamp,
            )
        except NoPriceForGivenTimestamp:
            usd_price = ZERO_PRICE

        return Balance(
            amount=self.pnl,
            usd_value=self.pnl * usd_price,
        )

    def to_db_tuple(self) -> ValidatorDailyStatsDBTuple:
        return (
            self.validator_index,
            self.timestamp,
            str(self.pnl),
        )

    @classmethod
    def deserialize_from_db(cls, entry: ValidatorDailyStatsDBTuple) -> 'ValidatorDailyStats':
        return cls(
            validator_index=entry[0],
            timestamp=Timestamp(entry[1]),
            pnl=FVal(entry[2]),
        )

    def serialize(self) -> dict[str, Any]:
        return {
            'validator_index': self.validator_index,
            'timestamp': self.timestamp,
            'pnl': self.pnl_balance.serialize(),
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'ValidatorDailyStats':
        """Deserializes a validator daily stats dict to ValidatorDailyStats object.
        May raise:
            - DeserializationError
            - KeyError
            - ValueError
        """
        return cls(
            validator_index=int(data['validator_index']),
            timestamp=deserialize_timestamp(data['timestamp']),
            pnl=deserialize_fval(
                value=data['pnl']['amount'],
                name='pnl',
                location='eth2 structure',
            ),
            ownership_percentage=ZERO,
        )
    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.timestamp

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.STAKING

    def get_identifier(self) -> str:
        return str(self.validator_index) + str(self.timestamp)

    def get_assets(self) -> list['Asset']:
        return [A_ETH, A_ETH2]

    def should_ignore(self, ignored_ids: set[str]) -> bool:
        return False

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        amount = self.pnl
        if amount == ZERO:
            return 1

        # This omits every acquisition event of `ETH2` if `eth_staking_taxable_after_withdrawal_enabled`  # noqa: E501
        if accounting.settings.eth_staking_taxable_after_withdrawal_enabled is True:
            return 1

        if self.pnl > ZERO:
            direction = EventDirection.IN
        else:
            direction = EventDirection.OUT
            amount = -amount

        accounting.add_asset_change_event(
            direction=direction,
            event_type=AccountingEventType.STAKING,
            notes='ETH2 staking daily PnL',
            location=Location.BLOCKCHAIN,
            timestamp=self.timestamp,
            asset=A_ETH2,
            amount=amount,
            taxable=True,
        )
        return 1


class ValidatorType(DBIntEnumMixIn):
    BLS = 0
    DISTRIBUTING = 1
    ACCUMULATING = 2

    @classmethod
    def deserialize(cls, value: str) -> 'ValidatorType':
        if value == '0x00':
            return cls.BLS
        if value == '0x01':
            return cls.DISTRIBUTING
        if value == '0x02':
            return cls.ACCUMULATING

        raise DeserializationError(f'Got unexpected value {value} for validator type')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ValidatorDetails:
    validator_index: int | None  # can be None if no index has yet been created due to not yet being seen by the consensus layer  # noqa: E501
    public_key: Eth2PubKey
    validator_type:  ValidatorType
    withdrawal_address: ChecksumEvmAddress | None = None  # only set if user has 0x01 or 0x02 credentials.  # noqa: E501
    activation_timestamp: Timestamp | None = None  # activation timestamp. None if not activated yet.  # noqa: E501
    withdrawable_timestamp: Timestamp | None = None  # the timestamp from which on a full withdrawal can happen. None if not exited and fully withdrawable yet  # noqa: E501
    exited_timestamp: Timestamp | None = None  # the timestamp at which the validator exited. None if we don't know it yet  # noqa: E501
    ownership_proportion: FVal = ONE  # [0, 1] proportion of ownership user has on the validator

    def __hash__(self) -> int:
        return hash(self.public_key)

    def serialize(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            'index': self.validator_index,
            'public_key': self.public_key,
            'validator_type': self.validator_type.serialize(),
        }
        if self.ownership_proportion != ONE:
            data['ownership_percentage'] = self.ownership_proportion.to_percentage(precision=2, with_perc_sign=False)  # noqa: E501

        for name in ('activation_timestamp', 'withdrawable_timestamp', 'withdrawal_address'):
            if (value := getattr(self, name)) is not None:
                data[name] = value

        return data

    def serialize_for_db(self) -> 'VALIDATOR_DETAILS_DB_TUPLE':
        """Serialize for DB insertion without touching the ownership proportion since
        the place this is inserted in the DB should not modify ownership"""
        return (
            self.validator_index,
            self.public_key,
            self.validator_type.serialize_for_db(),
            str(self.ownership_proportion),
            self.withdrawal_address,
            self.activation_timestamp,
            self.withdrawable_timestamp,
            self.exited_timestamp,
        )

    @classmethod
    def deserialize_from_db(cls, result: 'VALIDATOR_DETAILS_DB_TUPLE') -> Self:
        return cls(
            validator_index=result[0],
            public_key=result[1],
            validator_type=ValidatorType.deserialize_from_db(result[2]),
            ownership_proportion=FVal(result[3]),
            withdrawal_address=result[4],
            activation_timestamp=result[5],
            withdrawable_timestamp=result[6],
            exited_timestamp=result[7],
        )


class ValidatorStatus(StrEnum):
    PENDING = auto()
    ACTIVE = auto()
    EXITING = auto()
    EXITED = auto()
    CONSOLIDATED = auto()


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ValidatorDetailsWithStatus(ValidatorDetails):
    status: ValidatorStatus = ValidatorStatus.ACTIVE
    consolidated_into: int | None = None  # target validator index if consolidated

    def serialize(self) -> dict[str, Any]:
        result = super().serialize()
        result['status'] = str(self.status)
        if self.consolidated_into is not None:
            result['consolidated_into'] = self.consolidated_into

        return result

    def determine_status(self, exited_indices: set[int], consolidated_indices: dict[int, int]) -> None:  # noqa: E501
        if self.validator_index in consolidated_indices:
            self.status = ValidatorStatus.CONSOLIDATED
            self.consolidated_into = consolidated_indices[self.validator_index]
        elif self.validator_index in exited_indices:
            self.status = ValidatorStatus.EXITED
        elif self.withdrawable_timestamp is not None:
            self.status = ValidatorStatus.EXITING
        elif self.activation_timestamp is not None:
            self.status = ValidatorStatus.ACTIVE
        else:
            self.status = ValidatorStatus.PENDING


class PerformanceStatusFilter(StrEnum):
    """A smaller subset of validator statuses used by the frontend filtering

    Pending does not make sense for the places this is called as validators have no performance
    or daily stats. And since this is where we filter for now we use this also
    for the validators endpoint for consistency. If we want to filter by all statuses
    we can do it in the future.
    """
    ALL = auto()
    ACTIVE = auto()
    EXITED = auto()
    CONSOLIDATED = auto()
