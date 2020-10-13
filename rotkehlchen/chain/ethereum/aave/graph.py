import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.aave.common import (
    AAVE_RESERVE_TO_ASSET,
    ASSET_TO_AAVE_RESERVE_ADDRESS,
    _get_reserve_address_decimals,
)
from rotkehlchen.chain.ethereum.graph import Graph, get_common_params
from rotkehlchen.chain.ethereum.structures import AaveEvent
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now

from .common import AaveHistory, AaveInquirer

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)

USER_RESERVES_QUERY = """
{{
  userReserves(where: {{ user: "{address}"}}) {{
    id
    reserve{{
      id
      symbol
    }}
    user {{
      id
    }}
  }}
}}"""


DEPOSIT_EVENTS_QUERY = """
  deposits (orderBy: timestamp, orderDirection: asc, where: {
   user: $address, timestamp_lte: $end_ts, timestamp_gte: $start_ts
  }) {
    id
    amount
    referrer {
      id
    }
    reserve {
      id
    }
    timestamp
  }
}
"""

USER_EVENTS_QUERY = """
  users (where: {id: $address}) {
    id
    depositHistory {
        id
        amount
        reserve {
          id
        }
        timestamp
    }
    redeemUnderlyingHistory {
        id
        amount
        reserve {
          id
        }
        timestamp
    }
    reserves{
        id
        aTokenBalanceHistory {
          id
          balance
          userBalanceIndex
          interestRedirectionAddress
          redirectedBalance
          timestamp
        }
    }
  }
}
"""


class ATokenBalanceHistory(NamedTuple):
    reserve_address: ChecksumEthAddress
    balance: FVal
    tx_hash: str
    timestamp: Timestamp


class AaveUserReserve(NamedTuple):
    address: ChecksumEthAddress
    symbol: str


def _parse_atoken_balance_history(
        history: List[Dict[str, Any]],
        from_ts: Timestamp,
        to_ts: Timestamp,
) -> List[ATokenBalanceHistory]:
    result = []
    for entry in history:
        timestamp = entry['timestamp']
        if timestamp < from_ts or timestamp > to_ts:
            continue

        entry_id = entry['id']
        pairs = entry_id.split('0x')
        if len(pairs) != 4:
            log.error(
                f'Expected to find 3 hashes in graps\'s aTokenBalanceHistory '
                f'id but the encountered id does not match: {entry_id}. Skipping entry...',
            )
            continue

        reserve_address = to_checksum_address('0x' + pairs[2])
        tx_hash = '0x' + pairs[3]
        asset = AAVE_RESERVE_TO_ASSET.get(reserve_address, None)
        if asset is None:
            log.error(
                f'Unknown aave reserve address returned by atoken balance history '
                f' graph query: {reserve_address}. Skipping entry ...',
            )
            continue

        _, decimals = _get_reserve_address_decimals(asset.identifier)
        balance = token_normalized_value(int(entry['balance']), token_decimals=decimals)
        result.append(ATokenBalanceHistory(
            reserve_address=reserve_address,
            balance=balance,
            tx_hash=tx_hash,
            timestamp=timestamp,
        ))

    return result


class AaveGraphInquirer(AaveInquirer):
    """Reads Aave historical data from the graph protocol"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            premium: Optional[Premium],
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.graph = Graph('https://api.thegraph.com/subgraphs/name/aave/protocol-raw')

    def get_history_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
            to_block: int,
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
            if history_results is None:
                continue
            result[address] = history_results

        return result

    def _get_user_reserves(self, address: ChecksumEthAddress) -> List[AaveUserReserve]:
        query = self.graph.query(
            querystr=USER_RESERVES_QUERY.format(address=address.lower()),
        )
        result = []
        for entry in query['userReserves']:
            reserve = entry['reserve']
            result.append(AaveUserReserve(
                address=to_checksum_address(reserve['id']),
                symbol=reserve['symbol'],
            ))

        return result

    def _get_user_data(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            address: ChecksumEthAddress,
    ) -> AaveHistory:
        query = self.graph.query(
            querystr=USER_EVENTS_QUERY,
            param_types={'$address': 'ID!'},
            param_values={'address': address.lower()},
        )
        user_result = query['users'][0]
        deposits = self._parse_deposits(user_result['depositHistory'], from_ts, to_ts)
        withdrawals = self._parse_withdrawals(
            withdrawals=user_result['redeemUnderlyingHistory'],
            from_ts=from_ts,
            to_ts=to_ts,
        )

        reserve_history = {}
        for reserve in user_result['reserves']:
            pairs = reserve['id'].split('0x')
            if len(pairs) != 3:
                log.error(
                    f'Expected to find 2 hashes in graps\'s reserve history id '
                    f'but the encountered id does not match: {reserve["id"]}. Skipping entry...',
                )
            reserve_address = to_checksum_address('0x' + pairs[2])
            atoken_history = _parse_atoken_balance_history(
                history=reserve['aTokenBalanceHistory'],
                from_ts=from_ts,
                to_ts=to_ts,
            )
            reserve_history[reserve_address] = atoken_history

        actions = deposits + withdrawals
        actions.sort(key=lambda event: event.timestamp)
        atoken_balances: Dict[Asset, FVal] = defaultdict(FVal)
        interest_events: List[AaveEvent] = []
        total_earned: Dict[EthereumToken, Balance] = defaultdict(Balance)
        used_history_indices = set()
        for action in actions:
            if action.event_type == 'deposit':
                atoken_balances[action.asset] += action.value.amount
            else:  # withdrawal
                atoken_balances[action.asset] -= action.value.amount

            reserve_address = ASSET_TO_AAVE_RESERVE_ADDRESS.get(action.asset.identifier, None)  # type: ignore  # noqa: E501
            history = reserve_history.get(reserve_address, None)
            if history is None:
                log.error(
                    f'Could not find aTokenBalanceHistory for reserve '
                    f'{reserve_address} in an aave graph response.'
                    f' Skipping entry...',
                )
                continue
            history.sort(key=lambda event: event.timestamp)

            for idx, entry in enumerate(history):
                if idx in used_history_indices:
                    continue
                used_history_indices.add(idx)

                if entry.tx_hash == action.tx_hash:
                    diff = entry.balance - atoken_balances[action.asset]
                    if diff != ZERO:
                        atoken_balances[action.asset] = entry.balance
                        try:
                            asset = EthereumToken('a' + action.asset.identifier)
                        except UnknownAsset:
                            log.error(
                                f'Could not find corresponding aToken to'
                                f'{action.asset.identifier} during an aave graph uery'
                                f' Skipping entry...',
                            )
                            continue
                        timestamp = entry.timestamp
                        usd_price = query_usd_price_zero_if_error(
                            asset=asset,
                            time=timestamp,
                            location='aave interest event from graph query',
                            msg_aggregator=self.msg_aggregator,
                        )
                        earned_balance = Balance(amount=diff, usd_value=diff * usd_price)
                        interest_events.append(AaveEvent(
                            event_type='interest',
                            asset=asset,
                            value=earned_balance,
                            block_number=0,  # can't get from graph query
                            timestamp=timestamp,
                            tx_hash=entry.tx_hash,
                            # not really the log index, but should also be unique
                            log_index=action.log_index + 1,
                        ))
                        total_earned[asset] += earned_balance

                    # and once done break off the loop
                    break

                else:
                    # this atoken history is not due to an action, so skip it
                    # it's probably due to a simple transfer
                    atoken_balances[action.asset] = entry.balance
                    if action.event_type == 'deposit':
                        atoken_balances[action.asset] += action.value.amount
                    else:  # withdrawal
                        atoken_balances[action.asset] -= action.value.amount

        # Sort actions so that actions with same time are sorted deposit -> interest -> withdrawal
        events = interest_events + actions
        sort_map = {'deposit': 0, 'interest': 0.1, 'withdrawal': 0.2}
        events.sort(key=lambda event: sort_map[event.event_type] + event.timestamp)
        return AaveHistory(
            events=events,
            total_earned=total_earned,
        )

    def _parse_deposits(
            self,
            deposits: List[Dict[str, Any]],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[AaveEvent]:
        result = []
        for entry in deposits:
            timestamp = entry['timestamp']
            if timestamp < from_ts or timestamp > to_ts:
                # Since for the user data we can't query per timestamp, filter timestamps here
                continue

            pair = entry['id'].split(':')
            if len(pair) != 2:
                log.error(
                    f'Could not parse the id entry for an aave deposit as '
                    f'returned by graph: {entry["id"]}.  Skipping entry ...',
                )
                continue

            tx_hash = pair[0]
            index = int(pair[1])  # not really log index

            reserve_address = to_checksum_address(entry['reserve']['id'])
            asset = AAVE_RESERVE_TO_ASSET.get(reserve_address, None)
            if asset is None:
                log.error(
                    f'Unknown aave reserve address returned by graph query: '
                    f'{reserve_address}. Skipping entry ...',
                )
                continue

            _, decimals = _get_reserve_address_decimals(asset.identifier)
            amount = token_normalized_value(int(entry['amount']), token_decimals=decimals)
            usd_price = query_usd_price_zero_if_error(
                asset=asset,
                time=timestamp,
                location='aave deposit from graph query',
                msg_aggregator=self.msg_aggregator,
            )
            result.append(AaveEvent(
                event_type='deposit',
                asset=asset,
                value=Balance(amount=amount, usd_value=amount * usd_price),
                block_number=0,  # can't get from graph query
                timestamp=timestamp,
                tx_hash=tx_hash,
                log_index=index,  # not really the log index, but should also be unique
            ))

        return result

    def _parse_withdrawals(
            self,
            withdrawals: List[Dict[str, Any]],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[AaveEvent]:
        result = []
        for entry in withdrawals:
            timestamp = entry['timestamp']
            if timestamp < from_ts or timestamp > to_ts:
                # Since for the user data we can't query per timestamp, filter timestamps here
                continue

            pair = entry['id'].split(':')
            if len(pair) != 2:
                log.error(
                    f'Could not parse the id entry for an aave withdrawal as '
                    f'returned by graph: {entry["id"]}.  Skipping entry ...',
                )
                continue

            tx_hash = pair[0]
            index = int(pair[1])  # not really log index

            reserve_address = to_checksum_address(entry['reserve']['id'])
            asset = AAVE_RESERVE_TO_ASSET.get(reserve_address, None)
            if asset is None:
                log.error(
                    f'Unknown aave reserve address returned by graph query: '
                    f'{reserve_address}. Skipping entry ...',
                )
                continue

            _, decimals = _get_reserve_address_decimals(asset.identifier)
            amount = token_normalized_value(int(entry['amount']), token_decimals=decimals)
            usd_price = query_usd_price_zero_if_error(
                asset=asset,
                time=timestamp,
                location='aave withdrawal from graph query',
                msg_aggregator=self.msg_aggregator,
            )
            result.append(AaveEvent(
                event_type='withdrawal',
                asset=asset,
                value=Balance(amount=amount, usd_value=amount * usd_price),
                block_number=0,  # can't get from graph query
                timestamp=timestamp,
                tx_hash=tx_hash,
                log_index=index,  # not really the log index, but should also be unique
            ))

        return result

    def _get_deposits(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            address: ChecksumEthAddress,
    ) -> List[AaveEvent]:
        param_types, param_values = get_common_params(from_ts, to_ts, address, 'String!')
        query = self.graph.query(
            querystr=DEPOSIT_EVENTS_QUERY,
            param_types=param_types,
            param_values=param_values,
        )

        return self._parse_deposits(query['deposits'], from_ts, to_ts)

    def get_history_for_address(
            self,
            user_address: ChecksumEthAddress,
            to_block: int,
            atokens_list: Optional[List[EthereumToken]] = None,
            given_from_block: Optional[int] = None,
    ) -> Optional[AaveHistory]:
        """
        Queries aave history for a single address.

        This function should be entered while holding the history_lock
        semaphore
        """
        now = ts_now()
        reserves = self._get_user_reserves(address=user_address)
        if len(reserves) != 0:
            return self._get_user_data(from_ts=Timestamp(0), to_ts=now, address=user_address)

        return None
