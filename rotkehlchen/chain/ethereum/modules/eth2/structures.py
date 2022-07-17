import decimal
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Literal, NamedTuple, Optional, Tuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    EVMTxHash,
    Location,
    Timestamp,
    make_evm_tx_hash,
)
from rotkehlchen.utils.misc import from_gwei

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.assets.asset import Asset


class ValidatorID(NamedTuple):
    # not using index due to : https://github.com/python/mypy/issues/9043
    index: Optional[int]  # type: ignore  # may be null if the index is not yet determined
    public_key: Eth2PubKey
    ownership_proportion: FVal

    def __eq__(self, other: Any) -> bool:
        return self.public_key == other.public_key

    def __hash__(self) -> int:
        return hash(self.public_key)


Eth2ValidatorDBTuple = Tuple[int, str, str]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Eth2Validator:
    index: int
    public_key: Eth2PubKey
    ownership_proportion: FVal

    def serialize_for_db(self) -> Eth2ValidatorDBTuple:
        return self.index, self.public_key, str(self.ownership_proportion)

    @classmethod
    def deserialize_from_db(cls, result: Eth2ValidatorDBTuple) -> 'Eth2Validator':
        return cls(
            index=result[0],
            public_key=Eth2PubKey(result[1]),
            ownership_proportion=FVal(result[2]),
        )

    def serialize(self) -> Dict[str, Any]:
        percentage_value = self.ownership_proportion.to_percentage(precision=2, with_perc_sign=False)  # noqa: E501
        return {
            'validator_index': self.index,
            'public_key': self.public_key,
            'ownership_percentage': percentage_value,
        }


ValidatorDailyStatsDBTuple = Tuple[
    int,  # validator index
    int,  # timestamp
    str,  # usd_price_start
    str,  # usd_price_end
    str,  # pnl_amount
    str,  # start_balance
    str,  # end_balance
    int,  # missed_attestations
    int,  # orphaned_attestations
    int,  # proposed_blocks
    int,  # missed_blocks
    int,  # orphaned_blocks
    int,  # included_attester_slashings
    int,  # proposer_attester_slashings
    int,  # deposits_number
    str,  # amount_deposited
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ValidatorDailyStats(AccountingEventMixin):
    validator_index: int  # keeping the index here so it can be shown in accounting
    timestamp: Timestamp
    start_usd_price: FVal = ZERO
    end_usd_price: FVal = ZERO
    pnl: FVal = ZERO
    start_amount: FVal = ZERO
    end_amount: FVal = ZERO
    missed_attestations: int = 0
    orphaned_attestations: int = 0
    proposed_blocks: int = 0
    missed_blocks: int = 0
    orphaned_blocks: int = 0
    included_attester_slashings: int = 0
    proposer_attester_slashings: int = 0
    deposits_number: int = 0
    amount_deposited: FVal = ZERO
    ownership_percentage: FVal = ONE  # customized by get_eth2_history_events

    def __str__(self) -> str:
        return f'ETH2 validator {self.validator_index} daily stats'

    @property
    def pnl_balance(self) -> Balance:
        usd_price = (self.start_usd_price + self.end_usd_price) / 2
        return Balance(
            amount=self.pnl,
            usd_value=self.pnl * usd_price,
        )

    @property
    def start_balance(self) -> Balance:
        return Balance(
            amount=self.start_amount,
            usd_value=self.start_amount * self.start_usd_price,
        )

    @property
    def end_balance(self) -> Balance:
        return Balance(
            amount=self.end_amount,
            usd_value=self.end_amount * self.end_usd_price,
        )

    @property
    def deposited_balance(self) -> Balance:
        return Balance(
            amount=self.amount_deposited,
            usd_value=self.amount_deposited * self.start_usd_price,
        )

    def to_db_tuple(self) -> ValidatorDailyStatsDBTuple:
        return (
            self.validator_index,
            self.timestamp,
            str(self.start_usd_price),
            str(self.end_usd_price),
            str(self.pnl),
            str(self.start_amount),
            str(self.end_amount),
            self.missed_attestations,
            self.orphaned_attestations,
            self.proposed_blocks,
            self.missed_blocks,
            self.orphaned_blocks,
            self.included_attester_slashings,
            self.proposer_attester_slashings,
            self.deposits_number,
            str(self.amount_deposited),
        )

    @classmethod
    def deserialize_from_db(cls, entry: ValidatorDailyStatsDBTuple) -> 'ValidatorDailyStats':
        return cls(
            validator_index=entry[0],
            timestamp=Timestamp(entry[1]),
            start_usd_price=FVal(entry[2]),
            end_usd_price=FVal(entry[3]),
            pnl=FVal(entry[4]),
            start_amount=FVal(entry[5]),
            end_amount=FVal(entry[6]),
            missed_attestations=entry[7],
            orphaned_attestations=entry[8],
            proposed_blocks=entry[9],
            missed_blocks=entry[10],
            orphaned_blocks=entry[11],
            included_attester_slashings=entry[12],
            proposer_attester_slashings=entry[13],
            deposits_number=entry[14],
            amount_deposited=FVal(entry[15]),
        )

    def serialize(self) -> Dict[str, Any]:
        return {
            'validator_index': self.validator_index,
            'timestamp': self.timestamp,
            'pnl': self.pnl_balance.serialize(),
            'start_balance': self.start_balance.serialize(),
            'end_balance': self.end_balance.serialize(),
            'missed_attestations': self.missed_attestations,
            'orphaned_attestations': self.orphaned_attestations,
            'proposed_blocks': self.proposed_blocks,
            'missed_blocks': self.missed_blocks,
            'orphaned_blocks': self.orphaned_blocks,
            'included_attester_slashings': self.included_attester_slashings,
            'proposer_attester_slashings': self.proposer_attester_slashings,
            'deposits_number': self.deposits_number,
            'deposited_balance': self.deposited_balance.serialize(),
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'ValidatorDailyStats':
        """Deserializes a validator daily stats dict to ValidatorDailyStats object.
        May raise:
            - DeserializationError
            - KeyError
            - ValueError
        """
        try:
            start_usd_price = FVal(data['start_balance']['usd_value']) / FVal(data['start_balance']['amount'])  # noqa: 501
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            start_usd_price = ZERO
        try:
            end_usd_price = FVal(data['end_balance']['usd_value']) / FVal(data['end_balance']['amount'])  # noqa: 501
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            end_usd_price = ZERO
        return cls(
            validator_index=int(data['validator_index']),
            timestamp=deserialize_timestamp(data['timestamp']),
            start_usd_price=start_usd_price,
            end_usd_price=end_usd_price,
            pnl=deserialize_fval(
                value=data['pnl']['amount'],
                name='pnl',
                location='eth2 structure',
            ),
            start_amount=deserialize_fval(
                value=data['start_balance']['amount'],
                name='start_amount',
                location='eth2 structure',
            ),
            end_amount=deserialize_fval(
                value=data['end_balance']['amount'],
                name='end_amount',
                location='eth2 structure',
            ),
            missed_attestations=int(data['missed_attestations']),
            orphaned_attestations=int(data['orphaned_attestations']),
            proposed_blocks=int(data['proposed_blocks']),
            missed_blocks=int(data['missed_blocks']),
            orphaned_blocks=int(data['orphaned_blocks']),
            included_attester_slashings=int(data['included_attester_slashings']),
            proposer_attester_slashings=int(data['proposer_attester_slashings']),
            deposits_number=int(data['deposits_number']),
            amount_deposited=deserialize_fval(
                value=data['deposited_balance']['amount'],
                name='amount_deposited',
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

    def get_assets(self) -> List['Asset']:
        return [A_ETH, A_ETH2]

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        return False

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        amount = self.pnl_balance.amount
        if amount == ZERO:
            return 1

        # This omits every acquisition event of `ETH2` if `eth_staking_taxable_after_withdrawal_enabled`  # noqa: 501
        # setting is set to `True` until ETH2 is merged.
        if accounting.settings.eth_staking_taxable_after_withdrawal_enabled is True:
            return 1

        method: Literal['acquisition', 'spend']
        if self.pnl_balance.amount > ZERO:
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

    def serialize(self, eth_usd_price: FVal) -> Dict[str, Dict[str, str]]:
        return {
            'balance': _serialize_gwei_with_price(self.balance, eth_usd_price),
            'performance_1d': _serialize_gwei_with_price(self.performance_1d, eth_usd_price),
            'performance_1w': _serialize_gwei_with_price(self.performance_1w, eth_usd_price),
            'performance_1m': _serialize_gwei_with_price(self.performance_1m, eth_usd_price),
            'performance_1y': _serialize_gwei_with_price(self.performance_1y, eth_usd_price),
        }


DEPOSITING_VALIDATOR_PERFORMANCE = ValidatorPerformance(
    balance=32000000000,
    performance_1d=0,
    performance_1w=0,
    performance_1m=0,
    performance_1y=0,
)


Eth2DepositDBTuple = (
    Tuple[
        bytes,  # tx_hash
        int,    # tx_index
        str,    # from_address
        int,    # timestamp
        str,    # pubkey
        str,    # withdrawal_credentials
        str,    # amount
        str,    # usd_value
    ]
)


class ValidatorDetails(NamedTuple):
    validator_index: Optional[int]
    public_key: str
    eth1_depositor: ChecksumEvmAddress
    performance: ValidatorPerformance

    def serialize(self, eth_usd_price: FVal) -> Dict[str, Any]:
        return {
            'index': self.validator_index,
            'public_key': self.public_key,
            'eth1_depositor': self.eth1_depositor,
            **self.performance.serialize(eth_usd_price),
        }


class Eth2Deposit(NamedTuple):
    from_address: ChecksumEvmAddress
    pubkey: str  # hexstring
    withdrawal_credentials: str  # hexstring
    value: Balance
    tx_hash: EVMTxHash
    tx_index: int
    timestamp: Timestamp

    def serialize(self) -> Dict[str, Any]:
        result = self._asdict()  # pylint: disable=no-member
        result['tx_hash'] = self.tx_hash.hex()
        result['value'] = self.value.serialize()
        return result

    @classmethod
    def deserialize_from_db(
            cls,
            deposit_tuple: Eth2DepositDBTuple,
    ) -> 'Eth2Deposit':
        """Turns a tuple read from DB into an appropriate LiquidityPoolEvent.

        Deposit_tuple index - Schema columns
        ------------------------------------
        0 - tx_hash
        1 - tx_index
        2 - from_address
        3 - timestamp
        4 - pubkey
        5 - withdrawal_credentials
        6 - amount
        7 - usd_value
        """
        return cls(
            tx_hash=make_evm_tx_hash(deposit_tuple[0]),
            tx_index=int(deposit_tuple[1]),
            from_address=string_to_evm_address(deposit_tuple[2]),
            timestamp=Timestamp(int(deposit_tuple[3])),
            pubkey=deposit_tuple[4],
            withdrawal_credentials=deposit_tuple[5],
            value=Balance(amount=FVal(deposit_tuple[6]), usd_value=FVal(deposit_tuple[7])),
        )

    def to_db_tuple(self) -> Eth2DepositDBTuple:
        """Turns the instance data into a tuple to be inserted in the DB"""
        return (
            self.tx_hash,
            self.tx_index,
            str(self.from_address),
            int(self.timestamp),
            self.pubkey,
            self.withdrawal_credentials,
            str(self.value.amount),
            str(self.value.usd_value),
        )


def _serialize_gwei_with_price(value: int, eth_usd_price: FVal) -> Dict[str, str]:
    normalized_value = from_gwei(value)
    return {
        'amount': str(normalized_value),
        'usd_value': str(normalized_value * eth_usd_price),
    }
