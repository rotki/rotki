import logging
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.makerdao.common import RAY
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.chain.ethereum.zerion import GIVEN_DEFI_BALANCES
from rotkehlchen.constants.ethereum import (
    AAVE_ETH_RESERVE_ADDRESS,
    AAVE_LENDING_POOL,
    ATOKEN_ABI,
    ZERO_ADDRESS,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import (
    deserialize_blocknumber,
    deserialize_int_from_hex_or_int,
)
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

MAX_BLOCKTIME_CACHE_AAVE = 250  # 55 mins with 13 secs avg block time

ATOKEN_TO_DEPLOYED_BLOCK = {
    'aETH': 9241088,
    'aENJ': 10471941,
    'aDAI': 9241063,
    'aUSDC': 9241071,
    'aSUSD': 9241077,
    'aTUSD': 9241068,
    'aUSDT': 9241076,
    'aBUSD': 9747321,
    'aBAT': 9241085,
    'aKNC': 9241097,
    'aLEND': 9241081,
    'aLINK': 9241091,
    'aMANA': 9241110,
    'aMKR': 9241106,
    'aREP': 9241100,
    'aREN': 10472062,
    'aSNX': 9241118,
    'aWBTC': 9241225,
    'aYFI': 10748286,
    'aZRX': 9241114,
}
ATOKENS_LIST = [EthereumToken(x) for x in ATOKEN_TO_DEPLOYED_BLOCK]


class AaveLendingBalance(NamedTuple):
    """A balance for Aave lending.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    apy: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2),
        }


class AaveBorrowingBalance(NamedTuple):
    """A balance for Aave borrowing.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    variable_apr: FVal
    stable_apr: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'variable_apr': self.variable_apr.to_percentage(precision=2),
            'stable_apr': self.stable_apr.to_percentage(precision=2),
        }


class AaveBalances(NamedTuple):
    """The Aave balances per account. Using str for symbol since ETH is not a token"""
    lending: Dict[str, AaveLendingBalance]
    borrowing: Dict[str, AaveBorrowingBalance]


class AaveHistory(NamedTuple):
    """All events and total interest accrued for all Atoken of an address
    """
    events: List[AaveEvent]
    total_earned: Dict[EthereumToken, Balance]


def _get_reserve_address_decimals(symbol: str) -> Tuple[ChecksumEthAddress, int]:
    """Get the reserve address and the number of decimals for symbol"""
    if symbol == 'ETH':
        reserve_address = AAVE_ETH_RESERVE_ADDRESS
        decimals = 18
    else:
        token = EthereumToken(symbol)
        reserve_address = token.ethereum_address
        decimals = token.decimals

    return reserve_address, decimals


def _atoken_to_reserve_asset(atoken: EthereumToken) -> Asset:
    reserve_symbol = atoken.identifier[1:]
    if reserve_symbol == 'SUSD':
        reserve_symbol = 'sUSD'
    return Asset(reserve_symbol)


class Aave(EthereumModule):
    """Aave integration module

    https://docs.aave.com/developers/developing-on-aave/the-protocol/
    """

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()
        self.balances_lock = Semaphore()

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, AaveBalances]:
        with self.balances_lock:
            return self._get_balances(given_defi_balances)

    def _get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, AaveBalances]:
        """Retrieves the aave balances

        Receives the defi balances from zerion as an argument. They can either be directly given
        as the defi balances mapping or as a callable that will retrieve the
        balances mapping when executed.
        """
        aave_balances = {}
        reserve_cache: Dict[str, Tuple[Any, ...]] = {}

        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name != 'Aave':
                    continue

                # Depending on whether it's asset or debt we find what the reserve asset is
                if balance_entry.balance_type == 'Asset':
                    asset = balance_entry.underlying_balances[0]
                else:
                    asset = balance_entry.base_balance
                reserve_address, _ = _get_reserve_address_decimals(asset.token_symbol)

                reserve_data = reserve_cache.get(reserve_address, None)
                if reserve_data is None:
                    reserve_data = self.ethereum.call_contract(
                        contract_address=AAVE_LENDING_POOL.address,
                        abi=AAVE_LENDING_POOL.abi,
                        method_name='getReserveData',
                        arguments=[reserve_address],
                    )
                    reserve_cache[balance_entry.base_balance.token_symbol] = reserve_data

                if balance_entry.balance_type == 'Asset':
                    lending_map[asset.token_symbol] = AaveLendingBalance(
                        balance=asset.balance,
                        apy=FVal(reserve_data[4] / RAY),
                    )
                else:  # 'Debt'
                    borrowing_map[asset.token_symbol] = AaveBorrowingBalance(
                        balance=asset.balance,
                        variable_apr=FVal(reserve_data[5] / RAY),
                        stable_apr=FVal(reserve_data[6] / RAY),
                    )

            if lending_map == {} and borrowing_map == {}:
                # no aave balances for the account
                continue

            aave_balances[account] = AaveBalances(lending=lending_map, borrowing=borrowing_map)

        return aave_balances

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,  # pylint: disable=unused-argument
            to_timestamp: Timestamp,  # pylint: disable=unused-argument
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """Detects aave historical data for the given addresses"""
        result = {}
        latest_block = self.ethereum.get_latest_block_number()
        with self.history_lock:
            if reset_db_data is True:
                self.database.delete_aave_data()

            for address in addresses:
                last_query = self.database.get_used_query_range(f'aave_events_{address}')
                history_results = self.get_history_for_address(
                    user_address=address,
                    to_block=latest_block,
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
        if given_from_block is not None and to_block - given_from_block < MAX_BLOCKTIME_CACHE_AAVE:  # noqa: E501
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
        total_earned_map = {}
        for token in tokens:
            log.debug(
                f'Querying aave events for {user_address} and token '
                f'{token.identifier} with query_events={query_events}',
            )
            events = []
            if given_from_block:
                events.extend(self.database.get_aave_events(user_address, token))

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
                    total_balance += x.value
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
        return AaveHistory(events=total_address_events, total_earned=total_earned_map)

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
            amount = hex_or_bytes_to_int(event['data'])
            if amount == 0:
                continue  # first mint can be for 0. Ignore
            entry = (
                deserialize_blocknumber(event['blockNumber']),
                amount,
                self.ethereum.get_event_timestamp(event),
                event['transactionHash'],
            )
            mint_data.add(entry)
            mint_data_to_log_index[entry] = deserialize_int_from_hex_or_int(
                event['logIndex'], 'aave log index',
            )

        reserve_asset = _atoken_to_reserve_asset(atoken)
        reserve_address, decimals = _get_reserve_address_decimals(reserve_asset.identifier)
        aave_events = []
        for event in deposit_events:
            if hex_or_bytes_to_address(event['topics'][1]) == reserve_address:
                # first 32 bytes of the data are the amount
                deposit = hex_or_bytes_to_int(event['data'][:66])
                block_number = deserialize_blocknumber(event['blockNumber'])
                timestamp = self.ethereum.get_event_timestamp(event)
                tx_hash = event['transactionHash']
                log_index = deserialize_int_from_hex_or_int(event['logIndex'], 'aave log index')
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
                aave_events.append(AaveEvent(
                    event_type='deposit',
                    asset=reserve_asset,
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
            aave_events.append(AaveEvent(
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
                withdrawal = hex_or_bytes_to_int(event['data'][:66])
                block_number = deserialize_blocknumber(event['blockNumber'])
                timestamp = self.ethereum.get_event_timestamp(event)
                tx_hash = event['transactionHash']
                usd_price = query_usd_price_zero_if_error(
                    asset=reserve_asset,
                    time=timestamp,
                    location='aave withdrawal',
                    msg_aggregator=self.msg_aggregator,
                )
                withdrawal_amount = withdrawal / (FVal(10) ** FVal(decimals))
                aave_events.append(AaveEvent(
                    event_type='withdrawal',
                    asset=reserve_asset,
                    value=Balance(
                        amount=withdrawal_amount,
                        usd_value=withdrawal_amount * usd_price,
                    ),
                    block_number=block_number,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
                    log_index=deserialize_int_from_hex_or_int(event['logIndex'], 'aave log index'),
                ))

        return aave_events

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
