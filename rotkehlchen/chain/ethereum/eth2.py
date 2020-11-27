from typing import TYPE_CHECKING, Dict, List, NamedTuple, Tuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.utils import decode_event_data
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

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
        str,  # value
        int,  # validator_index
    ]
)


class Eth2Deposit(NamedTuple):
    from_address: ChecksumEthAddress
    pubkey: str  # hexstring
    withdrawal_credentials: str  # hexstring
    value: Balance
    validator_index: int  # the validator index
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
        6 - value
        7 - validator_index
        """
        return cls(
            tx_hash=deposit_tuple[0],
            log_index=int(deposit_tuple[1]),
            from_address=deserialize_ethereum_address(deposit_tuple[2]),
            timestamp=Timestamp(int(deposit_tuple[3])),
            pubkey=deposit_tuple[4],
            withdrawal_credentials=deposit_tuple[5],
            value=Balance(amount=FVal(deposit_tuple[6])),
            validator_index=int(deposit_tuple[7]),
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
            self.validator_index,
        )


class Eth2DepositResult(NamedTuple):
    deposits: List[Eth2Deposit]
    totals: Dict[ChecksumEthAddress, Balance]


def _get_eth2_staking_deposits_onchain(
        ethereum: 'EthereumManager',
        addresses: List[ChecksumEthAddress],
        has_premium: bool,
        msg_aggregator: MessagesAggregator,
        from_ts: Timestamp,
        to_ts: Timestamp,
) -> List[Eth2Deposit]:
    events = ETH2_DEPOSIT.get_logs(
        ethereum=ethereum,
        event_name='DepositEvent',
        argument_filters={},
        from_block=ETH2_DEPOSIT.deployed_block,
        to_block='latest',
    )
    transactions = ethereum.transactions.query(
        addresses=addresses,
        from_ts=from_ts,
        to_ts=to_ts,
        with_limit=False,
        recent_first=False,
    )
    deposits: List[Eth2Deposit] = []
    for transaction in transactions:
        if transaction.to_address != ETH2_DEPOSIT.address:
            continue

        tx_hash = '0x' + transaction.tx_hash.hex()
        for event in events:
            # Now find the corresponding event. If no event is found the transaction
            # probably failed or was something other than a deposit
            if event['transactionHash'] == tx_hash:
                decoded_data = decode_event_data(event['data'], EVENT_ABI)
                amount = int.from_bytes(decoded_data[2], byteorder='little')
                usd_price = ZERO
                if has_premium:  # won't show this to non-premium so don't bother
                    usd_price = query_usd_price_zero_if_error(
                        asset=A_ETH,
                        time=transaction.timestamp,
                        location='Eth2 staking query',
                        msg_aggregator=msg_aggregator,
                    )
                normalized_amount = FVal(amount) / 10 ** 9
                deposits.append(Eth2Deposit(
                    from_address=transaction.from_address,
                    pubkey='0x' + decoded_data[0].hex(),
                    withdrawal_credentials='0x' + decoded_data[1].hex(),
                    value=Balance(normalized_amount, usd_price * normalized_amount),
                    validator_index=int.from_bytes(decoded_data[4], byteorder='little'),
                    tx_hash=tx_hash,
                    log_index=event['logIndex'],
                    timestamp=Timestamp(transaction.timestamp),
                ))
                break
    return deposits


def get_eth2_staking_deposits(
        ethereum: 'EthereumManager',
        addresses: List[ChecksumEthAddress],
        has_premium: bool,
        msg_aggregator: MessagesAggregator,
        database: 'DBHandler',
) -> Eth2DepositResult:
    """Get the addresses' ETH2 staked amount

    For any given new address query on-chain from the ETH2 deposit contract
    deployment timestamp until now.

    For any existing address query on-chain from the minimum last used query
    range "end_ts" (among all the existing addresses) until now, as long as the
    difference between both is gte than REQUEST_DELTA_TS.

    Then write in DB all the new deposits and finally return them all.
    """
    new_deposits: List[Eth2Deposit] = []
    totals: Dict[ChecksumEthAddress, Balance] = {}
    new_addresses: List[ChecksumEthAddress] = []
    existing_addresses: List[ChecksumEthAddress] = []
    to_ts = ts_now()
    min_from_ts = to_ts

    # Get addresses' last used query range for ETH2 deposits
    for address in addresses:
        entry_name = f'{ETH2_DEPOSITS_PREFIX}_{address}'
        deposits_range = database.get_used_query_range(name=entry_name)

        if not deposits_range:
            new_addresses.append(address)
        else:
            existing_addresses.append(address)
            min_from_ts = min(min_from_ts, deposits_range[1])

    # Get deposits for new addresses
    if new_addresses:
        deposits_ = _get_eth2_staking_deposits_onchain(
            ethereum=ethereum,
            addresses=new_addresses,
            has_premium=has_premium,
            msg_aggregator=msg_aggregator,
            from_ts=ETH2_DEPLOYED_TS,
            to_ts=to_ts,
        )
        new_deposits.extend(deposits_)

        for address in new_addresses:
            entry_name = f'{ETH2_DEPOSITS_PREFIX}_{address}'
            database.update_used_query_range(
                name=entry_name,
                start_ts=ETH2_DEPLOYED_TS,
                end_ts=to_ts,
            )

    # Get new deposits for existing addresses
    if existing_addresses and min_from_ts + REQUEST_DELTA_TS <= to_ts:
        deposits_ = _get_eth2_staking_deposits_onchain(
            ethereum=ethereum,
            addresses=existing_addresses,
            has_premium=has_premium,
            msg_aggregator=msg_aggregator,
            from_ts=Timestamp(min_from_ts),
            to_ts=to_ts,
        )
        new_deposits.extend(deposits_)

        for address in existing_addresses:
            entry_name = f'{ETH2_DEPOSITS_PREFIX}_{address}'
            database.update_used_query_range(
                name=entry_name,
                start_ts=Timestamp(min_from_ts),
                end_ts=to_ts,
            )

    # Insert new deposits in DB
    if new_deposits:
        database.add_eth2_deposits(new_deposits)

    current_usd_price = Inquirer().find_usd_price(A_ETH)

    # Fetch all DB deposits for the given addresses
    deposits: List[Eth2Deposit] = []
    for address in addresses:
        db_deposits = database.get_eth2_deposits(address=address)
        if db_deposits:
            # Calculate total ETH2 balance per address
            total_amount = FVal(sum(db_deposit.value.amount for db_deposit in db_deposits))
            totals[address] = Balance(
                amount=total_amount,
                usd_value=total_amount * current_usd_price,
            )
            deposits.extend(db_deposits)

    deposits.sort(key=lambda deposit: (deposit.timestamp, deposit.log_index))
    return Eth2DepositResult(
        deposits=deposits,
        totals=totals,
    )
