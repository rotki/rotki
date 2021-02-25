from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.eth2_utils import get_validator_daily_stats
from rotkehlchen.chain.ethereum.typing import (
    DEPOSITING_VALIDATOR_PERFORMANCE,
    Eth2Deposit,
    ValidatorDetails,
)
from rotkehlchen.chain.ethereum.utils import decode_event_data
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.db.eth2 import ETH2_DEPOSITS_PREFIX, DBEth2
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import from_gwei, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.beaconchain import BeaconChain

ETH2_DEPOSIT = EthereumConstants().contract('ETH2_DEPOSIT')
ETH2_DEPLOYED_TS = Timestamp(1602667372)
EVENT_ABI = [x for x in ETH2_DEPOSIT.abi if x['type'] == 'event'][0]

REQUEST_DELTA_TS = 60 * 60  # 1


def _get_eth2_staking_deposits_onchain(
        ethereum: 'EthereumManager',
        addresses: List[ChecksumEthAddress],
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
                # all pylint ignores below due to https://github.com/PyCQA/pylint/issues/4114
                amount = int.from_bytes(decoded_data[2], byteorder='little')  # pylint: disable=unsubscriptable-object  # noqa: E501
                usd_price = query_usd_price_zero_if_error(
                    asset=A_ETH,
                    time=transaction.timestamp,
                    location='Eth2 staking query',
                    msg_aggregator=msg_aggregator,
                )
                normalized_amount = from_gwei(FVal(amount))
                deposits.append(Eth2Deposit(
                    from_address=transaction.from_address,
                    pubkey='0x' + decoded_data[0].hex(),    # pylint: disable=unsubscriptable-object  # noqa: E501
                    withdrawal_credentials='0x' + decoded_data[1].hex(),    # pylint: disable=unsubscriptable-object  # noqa: E501
                    value=Balance(normalized_amount, usd_price * normalized_amount),
                    deposit_index=int.from_bytes(decoded_data[4], byteorder='little'),    # pylint: disable=unsubscriptable-object  # noqa: E501
                    tx_hash=tx_hash,
                    log_index=event['logIndex'],
                    timestamp=Timestamp(transaction.timestamp),
                ))
                break

    return deposits


def get_eth2_staking_deposits(
        ethereum: 'EthereumManager',
        addresses: List[ChecksumEthAddress],
        msg_aggregator: MessagesAggregator,
        database: 'DBHandler',
) -> List[Eth2Deposit]:
    """Get the addresses' ETH2 staking deposits

    For any given new address query on-chain from the ETH2 deposit contract
    deployment timestamp until now.

    For any existing address query on-chain from the minimum last used query
    range "end_ts" (among all the existing addresses) until now, as long as the
    difference between both is gte than REQUEST_DELTA_TS.

    Then write in DB all the new deposits and finally return them all.
    """
    new_deposits: List[Eth2Deposit] = []
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

    dbeth2 = DBEth2(database)
    # Insert new deposits in DB
    if new_deposits:
        dbeth2.add_eth2_deposits(new_deposits)

    # Fetch all DB deposits for the given addresses
    deposits: List[Eth2Deposit] = []
    for address in addresses:
        db_deposits = dbeth2.get_eth2_deposits(address=address)
        deposits.extend(db_deposits)

    deposits.sort(key=lambda deposit: (deposit.timestamp, deposit.log_index))
    return deposits


def get_eth2_balances(
        beaconchain: 'BeaconChain',
        addresses: List[ChecksumEthAddress],
) -> Dict[ChecksumEthAddress, Balance]:
    """May Raise RemoteError from beaconcha.in api"""
    address_to_validators = {}
    index_to_address = {}
    validator_indices = []
    usd_price = Inquirer().find_usd_price(A_ETH)
    balance_mapping: Dict[ChecksumEthAddress, Balance] = defaultdict(Balance)
    # Map eth1 addresses to validators
    for address in addresses:
        validators = beaconchain.get_eth1_address_validators(address)
        if len(validators) == 0:
            continue

        address_to_validators[address] = validators
        for validator in validators:
            validator_indices.append(validator.validator_index)
            index_to_address[validator.validator_index] = address

    # Get current balance of all validator indices
    performance = beaconchain.get_performance(validator_indices)
    for validator_index, entry in performance.items():
        amount = from_gwei(entry.balance)
        balance_mapping[index_to_address[validator_index]] += Balance(amount, amount * usd_price)

    # The performance call does not return validators that are not active and are still depositing
    depositing_indices = set(index_to_address.keys()) - set(performance.keys())
    for index in depositing_indices:
        balance_mapping[index_to_address[index]] += Balance(
            amount=FVal('32'), usd_value=FVal('32') * usd_price,
        )

    return balance_mapping


def get_eth2_details(
        beaconchain: 'BeaconChain',
        addresses: List[ChecksumEthAddress],
) -> List[ValidatorDetails]:
    """Go through the list of eth1 addresses and find all eth2 validators associated
    with them along with their details. Also returns the daily stats for each validator.

    May raise RemoteError due to beaconcha.in API"""
    indices = []
    index_to_address = {}
    index_to_pubkey = {}
    assert beaconchain.db is not None, 'Beaconchain db should be populated'
    # and for each address get the validator info (to get the index) -- this could be avoided
    for address in addresses:
        validators = beaconchain.get_eth1_address_validators(address)
        for validator in validators:
            index_to_address[validator.validator_index] = address
            index_to_pubkey[validator.validator_index] = validator.public_key
            indices.append(validator.validator_index)

    # Get current balance of all validator indices
    result = []
    performance_result = beaconchain.get_performance(list(indices))
    for validator_index, entry in performance_result.items():
        stats = get_validator_daily_stats(
            db=beaconchain.db,
            validator_index=validator_index,
            msg_aggregator=beaconchain.msg_aggregator,
        )
        result.append(ValidatorDetails(
            validator_index=validator_index,
            public_key=index_to_pubkey[validator_index],
            eth1_depositor=index_to_address[validator_index],
            performance=entry,
            daily_stats=stats,
        ))

    # The performance call does not return validators that are not active and are still depositing
    depositing_indices = set(index_to_address.keys()) - set(performance_result.keys())
    for index in depositing_indices:
        stats = get_validator_daily_stats(
            db=beaconchain.db,
            validator_index=index,
            msg_aggregator=beaconchain.msg_aggregator,
        )
        result.append(ValidatorDetails(
            validator_index=index,
            public_key=index_to_pubkey[index],
            eth1_depositor=index_to_address[index],
            performance=DEPOSITING_VALIDATOR_PERFORMANCE,
            daily_stats=stats,
        ))

    return result
