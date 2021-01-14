from typing import Any, Dict, NamedTuple, Tuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.utils.misc import from_gwei

ETH2_DEPOSIT = EthereumConstants().contract('ETH2_DEPOSIT')
ETH2_DEPLOYED_TS = Timestamp(1602667372)
ETH2_DEPOSITS_PREFIX = 'eth2_deposits'

EVENT_ABI = [x for x in ETH2_DEPOSIT.abi if x['type'] == 'event'][0]

REQUEST_DELTA_TS = 60 * 60  # 1h

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
            from_address=deserialize_ethereum_address(deposit_tuple[2]),
            timestamp=Timestamp(int(deposit_tuple[3])),
            pubkey=deposit_tuple[4],
            withdrawal_credentials=deposit_tuple[5],
            value=Balance(amount=FVal(deposit_tuple[6]), usd_value=FVal(deposit_tuple[7])),
            deposit_index=int(deposit_tuple[8]),
        )

    def to_db_tuple(self) -> Eth2DepositDBTuple:
        """Turns the instance data into a tuple to be inserted in the DB
        """
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


class ValidatorBalance(NamedTuple):
    epoch: int
    balance: int  # in gwei
    effective_balance: int  # in wei


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


class ValidatorID(NamedTuple):
    # not using index due to : https://github.com/python/mypy/issues/9043
    validator_index: int
    public_key: str


class ValidatorDetails(NamedTuple):
    validator_index: int
    eth1_depositor: ChecksumEthAddress
    performance: ValidatorPerformance

    def serialize(self, eth_usd_price: FVal) -> Dict[str, Any]:
        return {
            'index': self.validator_index,
            'eth1_depositor': self.eth1_depositor,
            **self.performance.serialize(eth_usd_price),
        }
