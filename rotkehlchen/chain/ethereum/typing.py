from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from eth_typing import HexAddress, HexStr

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.utils.misc import from_gwei


def string_to_ethereum_address(value: str) -> ChecksumEthAddress:
    """This is a conversion without any checks of a string to ethereum address

    Is only used for typing.
    """
    return ChecksumEthAddress(HexAddress(HexStr(value)))


class NodeName(Enum):
    """Various node types

    Some open nodes taken from here: https://ethereumnodes.com/
    Related issue: https://github.com/rotki/rotki/issues/1716
    """
    OWN = 0
    ETHERSCAN = 1
    MYCRYPTO = 2
    BLOCKSCOUT = 3
    AVADO_POOL = 4
    ONEINCH = 5
    MYETHERWALLET = 6
    LINKPOOL = 7
    CLOUDFLARE_ETH = 8

    def __str__(self) -> str:
        if self == NodeName.OWN:
            return 'own node'
        if self == NodeName.ETHERSCAN:
            return 'etherscan'
        if self == NodeName.MYCRYPTO:
            return 'mycrypto'
        if self == NodeName.BLOCKSCOUT:
            return 'blockscout'
        if self == NodeName.AVADO_POOL:
            return 'avado pool'
        if self == NodeName.ONEINCH:
            return '1inch'
        if self == NodeName.MYETHERWALLET:
            return 'myetherwallet'
        if self == NodeName.LINKPOOL:
            return 'linkpool'
        if self == NodeName.CLOUDFLARE_ETH:
            return 'cloudflare-eth'
        # else
        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')

    def endpoint(self, own_rpc_endpoint: str) -> str:
        if self == NodeName.OWN:
            return own_rpc_endpoint
        if self == NodeName.ETHERSCAN:
            raise TypeError('Called endpoint for etherscan')
        if self == NodeName.MYCRYPTO:
            return 'https://api.mycryptoapi.com/eth'
        if self == NodeName.BLOCKSCOUT:
            return 'https://mainnet-nethermind.blockscout.com/'
        if self == NodeName.AVADO_POOL:
            return 'https://mainnet.eth.cloud.ava.do/'
        if self == NodeName.ONEINCH:
            return 'https://web3.1inch.exchange'
        if self == NodeName.MYETHERWALLET:
            return 'https://nodes.mewapi.io/rpc/eth'
        if self == NodeName.LINKPOOL:
            return 'https://main-rpc.linkpool.io/'
        if self == NodeName.CLOUDFLARE_ETH:
            return 'https://cloudflare-eth.com/'
        # else
        raise RuntimeError(f'Corrupt value {self} for NodeName -- Should never happen')


# Ethereum 2 stuff. Perhaps on its own file at some point?
class ValidatorID(NamedTuple):
    # not using index due to : https://github.com/python/mypy/issues/9043
    validator_index: Optional[int]  # may be null if the index is not yet determined
    public_key: str


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


class ValidatorDailyStats(NamedTuple):
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


def _serialize_gwei_with_price(value: int, eth_usd_price: FVal) -> Dict[str, str]:
    normalized_value = from_gwei(value)
    return {
        'amount': str(normalized_value),
        'usd_value': str(normalized_value * eth_usd_price),
    }


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
        str,  # tx_hash
        int,  # log_index
        str,  # from_address
        int,  # timestamp
        str,  # pubkey
        str,  # withdrawal_credentials
        str,  # amount
        str,  # usd_value
        int,  # validator_index
    ]
)


class ValidatorDetails(NamedTuple):
    validator_index: Optional[int]
    public_key: str
    eth1_depositor: ChecksumEthAddress
    performance: ValidatorPerformance
    daily_stats: List['ValidatorDailyStats']

    def serialize(self, eth_usd_price: FVal) -> Dict[str, Any]:
        return {
            'index': self.validator_index,
            'public_key': self.public_key,
            'eth1_depositor': self.eth1_depositor,
            **self.performance.serialize(eth_usd_price),
            'daily_stats': [x.serialize() for x in self.daily_stats],
        }


class Eth2Deposit(NamedTuple):
    from_address: ChecksumEthAddress
    pubkey: str  # hexstring
    withdrawal_credentials: str  # hexstring
    value: Balance
    deposit_index: int  # the deposit index -- not the same as the validator index
    tx_hash: str  # the transaction hash
    log_index: int
    timestamp: Timestamp

    @classmethod
    def deserialize_from_db(
            cls,
            deposit_tuple: Eth2DepositDBTuple,
    ) -> 'Eth2Deposit':
        """Turns a tuple read from DB into an appropriate LiquidityPoolEvent.

        Deposit_tuple index - Schema columns
        ------------------------------------
        0 - tx_hash
        1 - log_index
        2 - from_address
        3 - timestamp
        4 - pubkey
        5 - withdrawal_credentials
        6 - amount
        7 - usd_value
        8 - deposit_index
        """
        return cls(
            tx_hash=deposit_tuple[0],
            log_index=int(deposit_tuple[1]),
            from_address=string_to_ethereum_address(deposit_tuple[2]),
            timestamp=Timestamp(int(deposit_tuple[3])),
            pubkey=deposit_tuple[4],
            withdrawal_credentials=deposit_tuple[5],
            value=Balance(amount=FVal(deposit_tuple[6]), usd_value=FVal(deposit_tuple[7])),
            deposit_index=int(deposit_tuple[8]),
        )

    def to_db_tuple(self) -> Eth2DepositDBTuple:
        """Turns the instance data into a tuple to be inserted in the DB"""
        return (
            self.tx_hash,
            self.log_index,
            str(self.from_address),
            int(self.timestamp),
            self.pubkey,
            self.withdrawal_credentials,
            str(self.value.amount),
            str(self.value.usd_value),
            self.deposit_index,
        )
