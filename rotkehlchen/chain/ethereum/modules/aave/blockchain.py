import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.structures import (
    AaveDepositWithdrawalEvent,
    AaveEvent,
    AaveInterestEvent,
)
from rotkehlchen.constants.ethereum import (
    AAVE_LENDING_POOL,
    ATOKEN_ABI,
    MAX_BLOCKTIME_CACHE,
    ZERO_ADDRESS,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hexstr_to_int

from .common import AaveBalances, AaveHistory, AaveInquirer, _get_reserve_address_decimals
from .constants import ATOKENS_LIST, ATOKENV1_TO_ASSET

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)


class AaveBlockchainInquirer(AaveInquirer):
    """Reads Aave historical data from the chain by querying logs"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )

    def get_history_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
            to_block: int,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            aave_balances: Dict[ChecksumEthAddress, AaveBalances],  # pylint: disable=unused-argument  # noqa: E501
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """
        Queries aave history for a list of addresses.

        This function should be entered while holding the history_lock
        semaphore
        """
        result = {}
        for address in addresses:
            last_query = self.database.get_used_query_range(f'aave_events_{address}')
            history_results = self.get_history_for_address(
                user_address=address,
                to_block=to_block,
                given_from_block=last_query[1] + 1 if last_query is not None else None,
            )
            if len(history_results.events) == 0:
                continue
            result[address] = history_results

        return result

    def get_history_for_address(
            self,
            user_address: ChecksumEthAddress,
            to_block: int,
            atokens_list: Optional[List[EthereumToken]] = None,
            given_from_block: Optional[int] = None,
    ) -> AaveHistory:
        """
        Queries aave history for a single address.

        This function should be entered while holding the history_lock
        semaphore
        """
        # Get all deposit events for the address
        from_block = AAVE_LENDING_POOL.deployed_block if given_from_block is None else given_from_block  # noqa: E501
        argument_filters = {
            '_user': user_address,
        }
        query_events = True
        if given_from_block is not None and to_block - given_from_block < MAX_BLOCKTIME_CACHE:  # noqa: E501
            query_events = False  # Save time by not querying events if last query is recent

        deposit_events = []
        withdraw_events = []
        if query_events:
            deposit_events.extend(self.ethereum.get_logs(
                contract_address=AAVE_LENDING_POOL.address,
                abi=AAVE_LENDING_POOL.abi,
                event_name='Deposit',
                argument_filters=argument_filters,
                from_block=from_block,
                to_block=to_block,
            ))
            withdraw_events.extend(self.ethereum.get_logs(
                contract_address=AAVE_LENDING_POOL.address,
                abi=AAVE_LENDING_POOL.abi,
                event_name='RedeemUnderlying',
                argument_filters=argument_filters,
                from_block=from_block,
                to_block=to_block,
            ))

        # now for each atoken get all mint events and pass then to profit calculation
        tokens = atokens_list if atokens_list is not None else ATOKENS_LIST
        total_address_events = []
        total_earned_map: Dict[Asset, Balance] = {}
        for token in tokens:
            log.debug(
                f'Querying aave events for {user_address} and token '
                f'{token.identifier} with query_events={query_events}',
            )
            events = []
            if given_from_block:
                events.extend(self.database.get_aave_events(user_address, token))
                events = cast(List[AaveEvent], events)  # type: ignore

            new_events = []
            if query_events:
                new_events = self.get_events_for_atoken_and_address(
                    user_address=user_address,
                    atoken=token,
                    deposit_events=deposit_events,
                    withdraw_events=withdraw_events,
                    from_block=from_block,
                    to_block=to_block,
                )
                events.extend(new_events)
            total_balance = Balance()
            for x in events:
                if x.event_type == 'interest':
                    total_balance += x.value  # type: ignore

            # If the user still has balance in Aave we also need to see how much
            # accrued interest has not been yet paid out
            # TODO: ARCHIVE if to_block is not latest here we should get the balance
            # from the old block. Means using archive node
            balance = self.ethereum.call_contract(
                contract_address=token.ethereum_address,
                abi=ATOKEN_ABI,
                method_name='balanceOf',
                arguments=[user_address],
            )
            principal_balance = self.ethereum.call_contract(
                contract_address=token.ethereum_address,
                abi=ATOKEN_ABI,
                method_name='principalBalanceOf',
                arguments=[user_address],
            )

            if len(events) == 0 and balance == 0 and principal_balance == 0:
                # Nothing for this aToken for this address
                continue

            unpaid_interest = (balance - principal_balance) / (FVal(10) ** FVal(token.decimals))
            usd_price = Inquirer().find_usd_price(token)
            total_balance += Balance(
                amount=unpaid_interest,
                usd_value=unpaid_interest * usd_price,
            )
            total_earned_map[token] = total_balance
            total_address_events.extend(events)

            # now update the DB with the recently queried events
            self.database.add_aave_events(user_address, new_events)

        # After all events have been queried then also update the query range.
        # Even if no events are found for an address we need to remember the range
        self.database.update_used_block_query_range(
            name=f'aave_events_{user_address}',
            from_block=AAVE_LENDING_POOL.deployed_block,
            to_block=to_block,
        )

        total_address_events.sort(key=lambda event: event.timestamp)
        return AaveHistory(
            events=total_address_events,
            total_earned_interest=total_earned_map,
            total_lost={},
            total_earned_liquidations={},
        )

    def get_events_for_atoken_and_address(
            self,
            user_address: ChecksumEthAddress,
            atoken: EthereumToken,
            deposit_events: List[Dict[str, Any]],
            withdraw_events: List[Dict[str, Any]],
            from_block: int,
            to_block: int,
    ) -> List[AaveEvent]:
        """This function should be entered while holding the history_lock
        semaphore"""
        argument_filters = {
            'from': ZERO_ADDRESS,
            'to': user_address,
        }
        mint_events = self.ethereum.get_logs(
            contract_address=atoken.ethereum_address,
            abi=ATOKEN_ABI,
            event_name='Transfer',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )
        mint_data = set()
        mint_data_to_log_index = {}
        for event in mint_events:
            amount = hexstr_to_int(event['data'])
            if amount == 0:
                continue  # first mint can be for 0. Ignore
            entry = (
                event['blockNumber'],
                amount,
                self.ethereum.get_event_timestamp(event),
                event['transactionHash'],
            )
            mint_data.add(entry)
            mint_data_to_log_index[entry] = event['logIndex']

        reserve_asset = ATOKENV1_TO_ASSET[atoken]  # should never raise KeyError
        reserve_address, decimals = _get_reserve_address_decimals(reserve_asset)
        aave_events: List[AaveEvent] = []
        for event in deposit_events:
            if hex_or_bytes_to_address(event['topics'][1]) == reserve_address:
                # first 32 bytes of the data are the amount
                deposit = hexstr_to_int(event['data'][:66])
                block_number = event['blockNumber']
                timestamp = self.ethereum.get_event_timestamp(event)
                tx_hash = event['transactionHash']
                log_index = event['logIndex']
                # If there is a corresponding deposit event remove the minting event data
                entry = (block_number, deposit, timestamp, tx_hash)
                if entry in mint_data:
                    mint_data.remove(entry)
                    del mint_data_to_log_index[entry]

                usd_price = query_usd_price_zero_if_error(
                    asset=reserve_asset,
                    time=timestamp,
                    location='aave deposit',
                    msg_aggregator=self.msg_aggregator,
                )
                deposit_amount = deposit / (FVal(10) ** FVal(decimals))
                aave_events.append(AaveDepositWithdrawalEvent(
                    event_type='deposit',
                    asset=reserve_asset,
                    atoken=atoken,
                    value=Balance(
                        amount=deposit_amount,
                        usd_value=deposit_amount * usd_price,
                    ),
                    block_number=block_number,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
                    log_index=log_index,
                ))

        for data in mint_data:
            usd_price = query_usd_price_zero_if_error(
                asset=atoken,
                time=data[2],
                location='aave interest profit',
                msg_aggregator=self.msg_aggregator,
            )
            interest_amount = data[1] / (FVal(10) ** FVal(decimals))
            aave_events.append(AaveInterestEvent(
                event_type='interest',
                asset=atoken,
                value=Balance(
                    amount=interest_amount,
                    usd_value=interest_amount * usd_price,
                ),
                block_number=data[0],
                timestamp=data[2],
                tx_hash=data[3],
                log_index=mint_data_to_log_index[data],
            ))

        for event in withdraw_events:
            if hex_or_bytes_to_address(event['topics'][1]) == reserve_address:
                # first 32 bytes of the data are the amount
                withdrawal = hexstr_to_int(event['data'][:66])
                block_number = event['blockNumber']
                timestamp = self.ethereum.get_event_timestamp(event)
                tx_hash = event['transactionHash']
                usd_price = query_usd_price_zero_if_error(
                    asset=reserve_asset,
                    time=timestamp,
                    location='aave withdrawal',
                    msg_aggregator=self.msg_aggregator,
                )
                withdrawal_amount = withdrawal / (FVal(10) ** FVal(decimals))
                aave_events.append(AaveDepositWithdrawalEvent(
                    event_type='withdrawal',
                    asset=reserve_asset,
                    atoken=atoken,
                    value=Balance(
                        amount=withdrawal_amount,
                        usd_value=withdrawal_amount * usd_price,
                    ),
                    block_number=block_number,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
                    log_index=event['logIndex'],
                ))

        return aave_events
