from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.makerdao.common import RAY
from rotkehlchen.chain.ethereum.zerion import DefiProtocolBalances
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
from rotkehlchen.serialization.deserialize import deserialize_blocknumber
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager

ATOKEN_TO_DEPLOYED_BLOCK = {
    'aETH': 9241088,
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
    'aSNX': 9241118,
    'aWBTC': 9241225,
    'aZRX': 9241114,
}
ATOKENS_LIST = [EthereumToken(x) for x in ATOKEN_TO_DEPLOYED_BLOCK]


class AaveEvent(NamedTuple):
    """An event related to an Aave aToken

    Can be a deposit, withdrawal or interest payment

    The type of token not included here since these are in a mapping with a list
    per aToken so it would be redundant
    """
    event_type: Literal['deposit', 'withdrawal', 'interest']
    value: Balance
    block_number: int
    timestamp: Timestamp
    tx_hash: str


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
    """All events and total interest accrued for an Atoken and an address

    The type of token not included here since these are in a mapping with a list
    per aToken so it would be redundant
    """
    events: List[AaveEvent]
    total_earned: Balance


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

    def get_balances(
            self,
            defi_balances: Dict[ChecksumEthAddress, List[DefiProtocolBalances]],
    ) -> Dict[ChecksumEthAddress, AaveBalances]:
        aave_balances = {}
        reserve_cache: Dict[str, Tuple[Any, ...]] = {}
        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name != 'Aave':
                    continue

                # aave only has one underlying balance per base balance which
                # is what we will show. This is also the reserve asset
                asset = balance_entry.underlying_balances[0]
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
                        variable_apr=FVal(reserve_data[4] / RAY),
                        stable_apr=FVal(reserve_data[4] / RAY),
                    )

            if lending_map == {} and borrowing_map == {}:
                # no aave balances for the account
                continue

            aave_balances[account] = AaveBalances(lending=lending_map, borrowing=borrowing_map)

        return aave_balances

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, Dict[EthereumToken, AaveHistory]]:
        result = {}
        for address in addresses:
            profit_map = self.get_lending_profit_for_address(user_address=address)
            if profit_map == {}:
                continue
            result[address] = profit_map

        return result

    def get_lending_profit_for_address(
            self,
            user_address: ChecksumEthAddress,
            given_from_block: Optional[int] = None,
            given_to_block: Optional[int] = None,
            atokens_list: Optional[List[EthereumToken]] = None,
    ) -> Dict[EthereumToken, AaveHistory]:
        # Get all deposit events for the address
        from_block = AAVE_LENDING_POOL.deployed_block if given_from_block is None else given_from_block  # noqa: E501
        to_block: Union[int, Literal['latest']] = 'latest' if given_to_block is None else given_to_block  # noqa: E501
        argument_filters = {
            '_user': user_address,
        }
        deposit_events = self.ethereum.get_logs(
            contract_address=AAVE_LENDING_POOL.address,
            abi=AAVE_LENDING_POOL.abi,
            event_name='Deposit',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )
        withdraw_events = self.ethereum.get_logs(
            contract_address=AAVE_LENDING_POOL.address,
            abi=AAVE_LENDING_POOL.abi,
            event_name='RedeemUnderlying',
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )

        # now for each atoken get all mint events and pass then to profit calculation
        tokens = atokens_list if atokens_list is not None else ATOKENS_LIST
        profit_map = {}
        for token in tokens:
            events = self.get_events_for_atoken_and_address(
                user_address=user_address,
                atoken=token,
                deposit_events=deposit_events,
                withdraw_events=withdraw_events,
                given_from_block=given_from_block,
                given_to_block=given_to_block,
            )
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
            profit_map[token] = AaveHistory(events=events, total_earned=total_balance)

        return profit_map

    def get_events_for_atoken_and_address(
            self,
            user_address: ChecksumEthAddress,
            atoken: EthereumToken,
            deposit_events: List[Dict[str, Any]],
            withdraw_events: List[Dict[str, Any]],
            given_from_block: Optional[int] = None,
            given_to_block: Optional[int] = None,
    ) -> List[AaveEvent]:
        from_block = ATOKEN_TO_DEPLOYED_BLOCK[atoken.identifier] if given_from_block is None else given_from_block  # noqa: E501
        to_block: Union[int, Literal['latest']] = 'latest' if given_to_block is None else given_to_block  # noqa: E501
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
        for event in mint_events:
            amount = hex_or_bytes_to_int(event['data'])
            if amount == 0:
                continue  # first mint can be for 0. Ignore
            mint_data.add((
                deserialize_blocknumber(event['blockNumber']),
                amount,
                self.ethereum.get_event_timestamp(event),
                event['transactionHash'],
            ))

        reserve_address, decimals = _get_reserve_address_decimals(atoken.identifier[1:])
        aave_events = []
        for event in deposit_events:
            if hex_or_bytes_to_address(event['topics'][1]) == reserve_address:
                # first 32 bytes of the data are the amount
                deposit = hex_or_bytes_to_int(event['data'][:66])
                block_number = deserialize_blocknumber(event['blockNumber'])
                timestamp = self.ethereum.get_event_timestamp(event)
                tx_hash = event['transactionHash']
                # If there is a corresponding deposit event remove the minting event data
                if (block_number, deposit, timestamp, tx_hash) in mint_data:
                    mint_data.remove((block_number, deposit, timestamp, tx_hash))

                usd_price = query_usd_price_zero_if_error(
                    asset=atoken,
                    time=timestamp,
                    location='aave deposit',
                    msg_aggregator=self.msg_aggregator,
                )
                deposit_amount = deposit / (FVal(10) ** FVal(decimals))
                aave_events.append(AaveEvent(
                    event_type='deposit',
                    value=Balance(
                        amount=deposit_amount,
                        usd_value=deposit_amount * usd_price,
                    ),
                    block_number=block_number,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
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
                value=Balance(
                    amount=interest_amount,
                    usd_value=interest_amount * usd_price,
                ),
                block_number=data[0],
                timestamp=data[2],
                tx_hash=data[3],
            ))

        for event in withdraw_events:
            if hex_or_bytes_to_address(event['topics'][0]) == reserve_address:
                # first 32 bytes of the data are the amount
                withdrawal = hex_or_bytes_to_int(event['data'][:66])
                block_number = deserialize_blocknumber(event['blockNumber'])
                timestamp = self.ethereum.get_event_timestamp(event)
                tx_hash = event['transactionHash']
                usd_price = query_usd_price_zero_if_error(
                    asset=atoken,
                    time=timestamp,
                    location='aave withdrawal',
                    msg_aggregator=self.msg_aggregator,
                )
                withdrawal_amount = withdrawal / (FVal(10) ** FVal(decimals))
                aave_events.append(AaveEvent(
                    event_type='withdrawal',
                    value=Balance(
                        amount=withdrawal_amount,
                        usd_value=withdrawal_amount * usd_price,
                    ),
                    block_number=block_number,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
                ))

        aave_events.sort(key=lambda event: event.timestamp)
        return aave_events

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
