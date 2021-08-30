import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional

import gevent

from rotkehlchen.accounting.structures import AssetBalance, Balance
from rotkehlchen.chain.ethereum.eth2_utils import scrape_validator_daily_stats
from rotkehlchen.chain.ethereum.typing import (
    DEPOSITING_VALIDATOR_PERFORMANCE,
    Eth2Deposit,
    ValidatorDailyStats,
    ValidatorDetails,
)
from rotkehlchen.chain.ethereum.utils import decode_event_data
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.ethereum import EthereumConstants
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.eth2 import ETH2_DEPOSITS_PREFIX, DBEth2
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import from_gwei, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.beaconchain import BeaconChain

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ETH2_DEPOSIT = EthereumConstants().contract('ETH2_DEPOSIT')
ETH2_DEPLOYED_TS = Timestamp(1602667372)
EVENT_ABI = [x for x in ETH2_DEPOSIT.abi if x['type'] == 'event'][0]

REQUEST_DELTA_TS = 60 * 60  # 1

VALIDATOR_STATS_QUERY_BACKOFF_EVERY_N_VALIDATORS = 30
VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE = 20
VALIDATOR_STATS_QUERY_BACKOFF_TIME = 8


class Eth2(EthereumModule):
    """Module representation for Eth2"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
            beaconchain: 'BeaconChain',
    ) -> None:
        self.database = database
        self.premium = premium
        self.ethereum = ethereum_manager
        self.msg_aggregator = msg_aggregator
        self.beaconchain = beaconchain
        self.last_stats_query_ts = 0
        self.validator_stats_queried = 0

    def _get_eth2_staking_deposits_onchain(
            self,
            addresses: List[ChecksumEthAddress],
            msg_aggregator: MessagesAggregator,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[Eth2Deposit]:
        from_block = max(
            ETH2_DEPOSIT.deployed_block,
            self.ethereum.get_blocknumber_by_time(from_ts),
        )
        to_block = self.ethereum.get_blocknumber_by_time(to_ts)
        events = ETH2_DEPOSIT.get_logs(
            ethereum=self.ethereum,
            event_name='DepositEvent',
            argument_filters={},
            from_block=from_block,
            to_block=to_block,
        )

        filter_query = ETHTransactionsFilterQuery.make(
            order_ascending=True,  # oldest first
            limit=None,
            offset=None,
            addresses=addresses,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        transactions = self.ethereum.transactions.query(
            filter_query=filter_query,
            with_limit=False,
            only_cache=False,
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
                        location=f'Eth2 staking tx_hash: {tx_hash}',
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

    def get_staking_deposits(
            self,
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
            deposits_ = self._get_eth2_staking_deposits_onchain(
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
            deposits_ = self._get_eth2_staking_deposits_onchain(
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

    def get_balances(
            self,
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
            validators = self.beaconchain.get_eth1_address_validators(address)
            if len(validators) == 0:
                continue

            address_to_validators[address] = validators
            for validator in validators:
                if validator.validator_index is not None:
                    validator_indices.append(validator.validator_index)
                    index_to_address[validator.validator_index] = address
                else:
                    # Validator is early in depositing, and no index is known yet.
                    # Simply count 32 ETH balance for them
                    balance_mapping[address] += Balance(
                        amount=FVal('32'), usd_value=FVal('32') * usd_price,
                    )

        # Get current balance of all validator indices
        performance = self.beaconchain.get_performance(validator_indices)
        for validator_index, entry in performance.items():
            amount = from_gwei(entry.balance)
            balance_mapping[index_to_address[validator_index]] += Balance(amount, amount * usd_price)  # noqa: E501

        # Performance call does not return validators that are not active and are still depositing
        # So for them let's just count 32 ETH
        depositing_indices = set(index_to_address.keys()) - set(performance.keys())
        for index in depositing_indices:
            balance_mapping[index_to_address[index]] += Balance(
                amount=FVal('32'), usd_value=FVal('32') * usd_price,
            )

        return balance_mapping

    def get_details(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> List[ValidatorDetails]:
        """Go through the list of eth1 addresses and find all eth2 validators associated
        with them along with their details. Also returns the daily stats for each validator.

        May raise RemoteError due to beaconcha.in API"""
        indices = []
        index_to_address = {}
        index_to_pubkey = {}
        result = []
        assert self.beaconchain.db is not None, 'Beaconchain db should be populated'

        for address in addresses:
            validators = self.beaconchain.get_eth1_address_validators(address)
            for validator in validators:
                if validator.validator_index is None:
                    # for validators that are so early in the depositing queue that no
                    # validator index is confirmed yet let's return only the most basic info
                    result.append(ValidatorDetails(
                        validator_index=None,
                        public_key=validator.public_key,
                        eth1_depositor=address,
                        performance=DEPOSITING_VALIDATOR_PERFORMANCE,
                        daily_stats=[],
                    ))
                    continue

                index_to_address[validator.validator_index] = address
                index_to_pubkey[validator.validator_index] = validator.public_key
                indices.append(validator.validator_index)

        # Get current balance of all validator indices
        performance_result = self.beaconchain.get_performance(list(indices))
        for validator_index, entry in performance_result.items():
            stats = self.get_validator_daily_stats(
                validator_index=validator_index,
                msg_aggregator=self.msg_aggregator,
            )
            result.append(ValidatorDetails(
                validator_index=validator_index,
                public_key=index_to_pubkey[validator_index],
                eth1_depositor=index_to_address[validator_index],
                performance=entry,
                daily_stats=stats,
            ))

        # Performance call does not return validators that are not active and are still depositing
        depositing_indices = set(index_to_address.keys()) - set(performance_result.keys())
        for index in depositing_indices:
            stats = self.get_validator_daily_stats(
                validator_index=index,
                msg_aggregator=self.msg_aggregator,
            )
            result.append(ValidatorDetails(
                validator_index=index,
                public_key=index_to_pubkey[index],
                eth1_depositor=index_to_address[index],
                performance=DEPOSITING_VALIDATOR_PERFORMANCE,
                daily_stats=stats,
            ))

        return result

    def get_validator_daily_stats(
            self,
            validator_index: int,
            msg_aggregator: MessagesAggregator,
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
    ) -> List[ValidatorDailyStats]:
        """Gets the daily stats of an ETH2 validator by index

        First queries the DB for the already known stats and then if needed also scrapes
        the beacocha.in website for more. Saves all new entries to the DB.
        """
        dbeth2 = DBEth2(self.database)
        known_stats = dbeth2.get_validator_daily_stats(
            validator_index=validator_index,
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )
        last_ts = Timestamp(0) if len(known_stats) == 0 else known_stats[-1].timestamp
        limit_ts = to_timestamp if to_timestamp else ts_now()
        if limit_ts - last_ts <= DAY_IN_SECONDS:
            return known_stats  # no need to requery if less than a day passed

        now = ts_now()
        should_backoff = (
            now - self.last_stats_query_ts < VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE and
            self.validator_stats_queried >= VALIDATOR_STATS_QUERY_BACKOFF_EVERY_N_VALIDATORS
        )
        if should_backoff:
            log.debug(
                f'Queried {self.validator_stats_queried} validators in the last '
                f'{VALIDATOR_STATS_QUERY_BACKOFF_TIME_RANGE} seconds. Backing off for '
                f'{VALIDATOR_STATS_QUERY_BACKOFF_TIME} seconds.',
            )
            self.validator_stats_queried = 0
            gevent.sleep(VALIDATOR_STATS_QUERY_BACKOFF_TIME)

        new_stats = scrape_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=last_ts,
            msg_aggregator=msg_aggregator,
        )
        self.validator_stats_queried += 1
        self.last_stats_query_ts = now

        if len(new_stats) != 0:
            dbeth2.add_validator_daily_stats(stats=new_stats)

        return dbeth2.get_validator_daily_stats(
            validator_index=validator_index,
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        try:
            result = self.get_balances([address])
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Did not manage to query beaconcha.in api for address {address} due to {str(e)}.'
                f' If you have Eth2 staked balances the final balance results may not be accurate',
            )
            return None
        balance = result.get(address)
        if balance is None:
            return None

        return [AssetBalance(asset=A_ETH2, balance=balance)]

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_eth2_deposits()
        self.database.delete_eth2_daily_stats()
