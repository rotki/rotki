from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Location, Timestamp
from rotkehlchen.utils.misc import from_gwei

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.accounting.structures import ACCOUNTING_METHOD_TYPE


class ValidatorID(NamedTuple):
    # not using index due to : https://github.com/python/mypy/issues/9043
    index: Optional[int]  # type: ignore  # may be null if the index is not yet determined
    public_key: Eth2PubKey
    ownership_proportion: FVal

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NamedTuple) and self.public_key == other.public_key  # type: ignore  # ignore is due to isinstance not recognized

    def __hash__(self) -> int:
        return hash(self.public_key)


Eth2ValidatorDBTuple = tuple[int, str, str]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Eth2Validator:
    index: int
    public_key: Eth2PubKey
    ownership_proportion: FVal = ONE

    def serialize_for_db(self) -> Eth2ValidatorDBTuple:
        return self.index, self.public_key, str(self.ownership_proportion)

    @classmethod
    def deserialize_from_db(cls, result: Eth2ValidatorDBTuple) -> 'Eth2Validator':
        return cls(
            index=result[0],
            public_key=Eth2PubKey(result[1]),
            ownership_proportion=FVal(result[2]),
        )

    def serialize(self) -> dict[str, Any]:
        percentage_value = self.ownership_proportion.to_percentage(precision=2, with_perc_sign=False)  # noqa: E501
        return {
            'validator_index': self.index,
            'public_key': self.public_key,
            'ownership_percentage': percentage_value,
        }


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
    ownership_percentage: FVal = ONE  # customized by get_eth2_history_events

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

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
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

        method: ACCOUNTING_METHOD_TYPE
        if self.pnl > ZERO:
            method = 'acquisition'
        else:
            method = 'spend'
            amount = -amount
        accounting.add_asset_change_event(
            method=method,
            event_type=AccountingEventType.STAKING,
            notes='ETH2 staking daily PnL',
            location=Location.BLOCKCHAIN,
            timestamp=self.timestamp,
            asset=A_ETH2,
            amount=amount,
            taxable=True,
        )
        return 1


class ValidatorPerformance(NamedTuple):
    balance: int  # in gwei
    performance_1d: int  # in gwei
    performance_1w: int  # in gwei
    performance_1m: int  # in gwei
    performance_1y: int  # in gwei
    performance_total: int  # in gwei

    def serialize(self, eth_usd_price: FVal) -> dict[str, dict[str, str]]:
        return {
            'balance': _serialize_gwei_with_price(self.balance, eth_usd_price),
            'performance_1d': _serialize_gwei_with_price(self.performance_1d, eth_usd_price),
            'performance_1w': _serialize_gwei_with_price(self.performance_1w, eth_usd_price),
            'performance_1m': _serialize_gwei_with_price(self.performance_1m, eth_usd_price),
            'performance_1y': _serialize_gwei_with_price(self.performance_1y, eth_usd_price),
            'performance_total': _serialize_gwei_with_price(self.performance_total, eth_usd_price),
        }


DEPOSITING_VALIDATOR_PERFORMANCE = ValidatorPerformance(
    balance=32000000000,
    performance_1d=0,
    performance_1w=0,
    performance_1m=0,
    performance_1y=0,
    performance_total=0,
)


class ValidatorDetails(NamedTuple):
    validator_index: Optional[int]
    public_key: str
    eth1_depositor: Optional[ChecksumEvmAddress]
    has_exited: bool
    performance: ValidatorPerformance

    def serialize(self, eth_usd_price: FVal) -> dict[str, Any]:
        return {
            'index': self.validator_index,
            'public_key': self.public_key,
            'eth1_depositor': self.eth1_depositor,
            'has_exited': self.has_exited,
            **self.performance.serialize(eth_usd_price),
        }


def _serialize_gwei_with_price(value: int, eth_usd_price: FVal) -> dict[str, str]:
    normalized_value = from_gwei(value)
    return {
        'amount': str(normalized_value),
        'usd_value': str(normalized_value * eth_usd_price),
    }
