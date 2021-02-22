import logging
import operator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.accounting.structures import AssetBalance, Balance, DefiEvent, DefiEventType
from .common import (
    MAKERDAO_REQUERY_PERIOD,
    RAD,
    RAY,
    MakerdaoCommon,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.ethereum import MAKERDAO_DAI_JOIN, MAKERDAO_POT
from rotkehlchen.errors import BlockchainQueryError, ConversionError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_or_use_default
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hexstr_to_int, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)

POT_CREATION_TIMESTAMP = 1573672721
CHI_BLOCKS_SEARCH_DISTANCE = 250  # Blocks per call query per side (before/after)
MAX_BLOCKS_TO_QUERY = 346000  # query about a month's worth of blocks in each side before giving up


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMovement:
    movement_type: Literal['deposit', 'withdrawal']
    address: ChecksumEthAddress
    # normalized balance in DSR DAI (RAD precision 10**45)
    normalized_balance: int
    # gain so far in DSR DAI (RAD precision 10**45)
    gain_so_far: int = field(init=False)
    gain_so_far_usd_value: FVal = field(init=False)
    # dai balance in DSR DAI (RAD precision 10**45)
    amount: int
    amount_usd_value: FVal
    block_number: int
    timestamp: Timestamp
    tx_hash: str

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return f'Makerdao DSR {self.movement_type}'


class DSRCurrentBalances(NamedTuple):
    balances: Dict[ChecksumEthAddress, Balance]
    # The percentage of the current DSR. e.g. 8% would be 8.00
    current_dsr: FVal


class DSRGain(NamedTuple):
    """Represents a DSR gain in a given period

    amount is the total gain and tx_hashes contains all transactions involved
    """
    amount: FVal
    from_timestamp: Timestamp
    to_timestamp: Timestamp
    tx_hashes: List[str]


class DSRAccountReport(NamedTuple):
    movements: List[DSRMovement]
    gain_so_far: int
    gain_so_far_usd_value: FVal

    def serialize(self) -> Dict[str, Any]:
        serialized_report = {
            'gain_so_far': {
                'amount': str(_dsrdai_to_dai(self.gain_so_far)),
                'usd_value': str(self.gain_so_far_usd_value),
            },
            'movements': [],
        }
        for movement in self.movements:
            serialized_movement = {
                'movement_type': movement.movement_type,
                'gain_so_far': {
                    'amount': str(_dsrdai_to_dai(movement.gain_so_far)),
                    'usd_value': str(movement.gain_so_far_usd_value),
                },
                'value': {
                    'amount': str(_dsrdai_to_dai(movement.amount)),
                    'usd_value': str(movement.amount_usd_value),
                },
                'block_number': movement.block_number,
                'timestamp': movement.timestamp,
                'tx_hash': movement.tx_hash,
            }
            serialized_report['movements'].append(serialized_movement)  # type: ignore
        return serialized_report


def _dsrdai_to_dai(value: Union[int, FVal]) -> FVal:
    """Turns a big integer that is the value of DAI in DSR into a proper DAI decimal FVal"""
    return FVal(value / FVal(RAD))


class ChiRetrievalError(Exception):
    pass


def _find_closest_event(
        join_events: List[Dict[str, Any]],
        exit_events: List[Dict[str, Any]],
        index: int,
        comparison: Callable,
) -> Optional[Dict[str, Any]]:
    """Given lists of events and index/comparisonop find the closest event

    Index and comparisonon depend on whether we are searching for the events
    backwards or forwards.
    """
    found_event = None
    if len(join_events) != 0:
        found_event = join_events[index]
    if len(exit_events) != 0:
        if found_event:
            join_number = found_event['blockNumber']
            exit_number = exit_events[index]['blockNumber']

            if comparison(exit_number, join_number):
                found_event = exit_events[index]
        else:
            found_event = exit_events[index]

    return found_event


class MakerdaoDsr(MakerdaoCommon):

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
        self.reset_last_query_ts()
        self.historical_dsr_reports: Dict[ChecksumEthAddress, DSRAccountReport] = {}
        self.lock = Semaphore()

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        super().reset_last_query_ts()
        self.last_historical_dsr_query_ts = 0

    def get_current_dsr(self) -> DSRCurrentBalances:
        """Gets the current DSR balance for all accounts that have DAI in DSR
        and the current DSR percentage

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        with self.lock:
            proxy_mappings = self._get_accounts_having_maker_proxy()
            balances = {}
            try:
                current_dai_price = Inquirer().find_usd_price(A_DAI)
            except RemoteError:
                current_dai_price = Price(FVal(1))
            for account, proxy in proxy_mappings.items():
                guy_slice = MAKERDAO_POT.call(self.ethereum, 'pie', arguments=[proxy])
                if guy_slice == 0:
                    # no current DSR balance for this proxy
                    continue
                chi = MAKERDAO_POT.call(self.ethereum, 'chi')
                dai_balance = _dsrdai_to_dai(guy_slice * chi)
                balances[account] = Balance(
                    amount=dai_balance,
                    usd_value=current_dai_price * dai_balance,
                )

            current_dsr = MAKERDAO_POT.call(self.ethereum, 'dsr')
            # Calculation is from here:
            # https://docs.makerdao.com/smart-contract-modules/rates-module#a-note-on-setting-rates
            current_dsr_percentage = ((FVal(current_dsr / RAY) ** 31622400) % 1) * 100
            result = DSRCurrentBalances(balances=balances, current_dsr=current_dsr_percentage)

        return result

    def _get_vat_join_exit_at_transaction(
            self,
            movement_type: Literal['join', 'exit'],
            proxy_address: ChecksumEthAddress,
            block_number: int,
            transaction_index: int,
    ) -> Optional[int]:
        """Returns values in DSR DAI that were deposited/withdrawn at a block number and tx index

        DSR DAI means they need they have a lot more digits than normal DAI and they
        need to be divided by RAD (10**45) in order to get real DAI value. Keeping
        it like that since most calculations deal with RAD precision in DSR.

        Returns None if no value was found of if there was an error with conversion.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        argument_filters = {
            'sig': '0x3b4da69f' if movement_type == 'join' else '0xef693bed',
            'usr': proxy_address,
        }
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_DAI_JOIN.address,
            abi=MAKERDAO_DAI_JOIN.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=block_number,
            to_block=block_number,
        )
        value = None
        for event in events:
            if event['transactionIndex'] == transaction_index:
                if value is not None:
                    log.error(  # type: ignore
                        'Mistaken assumption: There is multiple vat.move events for '
                        'the same transaction',
                    )
                try:
                    value = hexstr_to_int(event['topics'][3])
                    break
                except ConversionError:
                    value = None
        return value * RAY  # turn it from DAI to RAD

    def _historical_dsr_for_account(
            self,
            account: ChecksumEthAddress,
            proxy: ChecksumEthAddress,
    ) -> DSRAccountReport:
        """Creates a historical DSR report for a single account

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        movements = []
        join_normalized_balances = []
        exit_normalized_balances = []
        argument_filters = {
            'sig': '0x049878f3',  # join
            'usr': proxy,
        }
        join_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_POT.deployed_block,
        )
        for join_event in join_events:
            try:
                wad_val = hexstr_to_int(join_event['topics'][2])
            except ConversionError as e:
                msg = f'Error at reading DSR join event topics. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            join_normalized_balances.append(wad_val)

            # and now get the deposit amount
            block_number = join_event['blockNumber']
            dai_value = self._get_vat_join_exit_at_transaction(
                movement_type='join',
                proxy_address=proxy,
                block_number=block_number,
                transaction_index=join_event['transactionIndex'],
            )
            if dai_value is None:
                self.msg_aggregator.add_error(
                    'Did not find corresponding vat.move event for pot join. Skipping ...',
                )
                continue

            timestamp = self.ethereum.get_event_timestamp(join_event)
            usd_price = query_usd_price_or_use_default(
                asset=A_DAI,
                time=timestamp,
                default_value=FVal(1),
                location='DSR deposit',
            )
            movements.append(
                DSRMovement(
                    movement_type='deposit',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    amount_usd_value=_dsrdai_to_dai(dai_value) * usd_price,
                    block_number=join_event['blockNumber'],
                    timestamp=timestamp,
                    tx_hash=join_event['transactionHash'],
                ),
            )

        argument_filters = {
            'sig': '0x7f8661a1',  # exit
            'usr': proxy,
        }
        exit_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=MAKERDAO_POT.deployed_block,
        )
        for exit_event in exit_events:
            try:
                wad_val = hexstr_to_int(exit_event['topics'][2])
            except ConversionError as e:
                msg = f'Error at reading DSR exit event topics. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            exit_normalized_balances.append(wad_val)

            block_number = exit_event['blockNumber']
            # and now get the withdrawal amount
            dai_value = self._get_vat_join_exit_at_transaction(
                movement_type='exit',
                proxy_address=proxy,
                block_number=block_number,
                transaction_index=exit_event['transactionIndex'],
            )
            if dai_value is None:
                self.msg_aggregator.add_error(
                    'Did not find corresponding vat.move event for pot exit. Skipping ...',
                )
                continue

            timestamp = self.ethereum.get_event_timestamp(exit_event)
            usd_price = query_usd_price_or_use_default(
                asset=A_DAI,
                time=timestamp,
                default_value=FVal(1),
                location='DSR withdrawal',
            )
            movements.append(
                DSRMovement(
                    movement_type='withdrawal',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    amount_usd_value=_dsrdai_to_dai(dai_value) * usd_price,
                    block_number=exit_event['blockNumber'],
                    timestamp=timestamp,
                    tx_hash=exit_event['transactionHash'],
                ),
            )

        normalized_balance = 0
        amount_in_dsr = 0
        movements.sort(key=lambda x: x.block_number)

        for idx, m in enumerate(movements):
            if m.normalized_balance == 0:
                # skip 0 amount/balance movements. Consider last gain as last gain so far.
                if idx == 0:
                    m.gain_so_far = 0
                    m.gain_so_far_usd_value = ZERO
                else:
                    m.gain_so_far = movements[idx - 1].gain_so_far
                    m.gain_so_far_usd_value = movements[idx - 1].gain_so_far_usd_value
                continue

            if normalized_balance == m.normalized_balance:
                m.gain_so_far = m.amount - amount_in_dsr
            else:
                current_chi = FVal(m.amount) / FVal(m.normalized_balance)
                gain_so_far = normalized_balance * current_chi - amount_in_dsr
                m.gain_so_far = gain_so_far.to_int(exact=False)

            usd_price = query_usd_price_or_use_default(
                asset=A_DAI,
                time=m.timestamp,
                default_value=FVal(1),
                location='DSR movement',
            )
            m.gain_so_far_usd_value = _dsrdai_to_dai(m.gain_so_far) * usd_price
            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance

        chi = MAKERDAO_POT.call(self.ethereum, 'chi')
        normalized_balance = normalized_balance * chi
        gain = normalized_balance - amount_in_dsr
        try:
            current_dai_price = Inquirer().find_usd_price(A_DAI)
        except RemoteError:
            current_dai_price = Price(FVal(1))

        # Calculate the total gain so far in USD
        unaccounted_gain = _dsrdai_to_dai(gain)
        last_usd_value = ZERO
        last_dai_gain = 0
        if len(movements) != 0:
            last_usd_value = movements[-1].gain_so_far_usd_value
            last_dai_gain = movements[-1].gain_so_far
            unaccounted_gain = _dsrdai_to_dai(gain - last_dai_gain)
        gain_so_far_usd_value = unaccounted_gain * current_dai_price + last_usd_value

        return DSRAccountReport(
            movements=movements,
            gain_so_far=gain,
            gain_so_far_usd_value=gain_so_far_usd_value,
        )

    def get_historical_dsr(self) -> Dict[ChecksumEthAddress, DSRAccountReport]:
        """Gets the historical DSR report per account

            This is a premium only call. Check happens only in the API level.
        """
        now = ts_now()
        if now - self.last_historical_dsr_query_ts < MAKERDAO_REQUERY_PERIOD:
            return self.historical_dsr_reports

        with self.lock:
            proxy_mappings = self._get_accounts_having_maker_proxy()
            reports = {}
            for account, proxy in proxy_mappings.items():
                report = self._historical_dsr_for_account(account, proxy)
                if len(report.movements) == 0:
                    # This proxy has never had any DSR events
                    continue

                reports[account] = report

        self.historical_dsr_reports = reports
        self.last_historical_dsr_query_ts = ts_now()
        return self.historical_dsr_reports

    def get_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> List[DefiEvent]:
        """Gets the history events from DSR for accounting

            This is a premium only call. Check happens only in the API level.
        """
        history = self.get_historical_dsr()
        events = []
        for _, report in history.items():
            total_balance = Balance()
            counted_profit = Balance()
            for movement in report.movements:
                if movement.timestamp < from_timestamp:
                    continue
                if movement.timestamp > to_timestamp:
                    break

                pnl = got_asset = got_balance = spent_asset = spent_balance = None  # noqa: E501
                balance = Balance(
                    amount=_dsrdai_to_dai(movement.amount),
                    usd_value=movement.amount_usd_value,
                )
                if movement.movement_type == 'deposit':
                    spent_asset = A_DAI
                    spent_balance = balance
                    total_balance -= balance
                else:
                    got_asset = A_DAI
                    got_balance = balance
                    total_balance += balance
                    if total_balance.amount - counted_profit.amount > ZERO:
                        pnl_balance = total_balance - counted_profit
                        counted_profit += pnl_balance
                        pnl = [AssetBalance(asset=A_DAI, balance=pnl_balance)]

                events.append(DefiEvent(
                    timestamp=movement.timestamp,
                    wrapped_event=movement,
                    event_type=DefiEventType.DSR_EVENT,
                    got_asset=got_asset,
                    got_balance=got_balance,
                    spent_asset=spent_asset,
                    spent_balance=spent_balance,
                    pnl=pnl,
                    # Depositing and withdrawing from DSR is not counted in
                    # cost basis. DAI were always yours, you did not rebuy them
                    count_spent_got_cost_basis=False,
                    tx_hash=movement.tx_hash,
                ))

        return events

    def _get_join_exit_events(
            self,
            from_block: int,
            to_block: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        join_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters={'sig': '0x049878f3'},  # join
            from_block=from_block,
            to_block=to_block,
        )
        exit_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT.address,
            abi=MAKERDAO_POT.abi,
            event_name='LogNote',
            argument_filters={'sig': '0x7f8661a1'},  # exit
            from_block=from_block,
            to_block=to_block,
        )
        return join_events, exit_events

    def _try_get_chi_close_to(self, time: Timestamp) -> FVal:
        """Best effort attempt to get a chi value close to the given timestamp

        It can't be 100% accurate since we use the logs of join() or exit()
        in order to find the closest time chi was changed. It also may not work
        if for some reason there is no logs in the block range we are looking for.

        Better solution would have been an archive node's query.

        May raise:
        - RemoteError if there are problems with querying etherscan
        - ChiRetrievalError if we are unable to query chi at the given timestamp
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """

        if time > 1584386100:
            # If the time is after 16/03/2020 19:15 GMT we know that
            # makerdao DSR was set to 0% we know chi has not changed
            # https://twitter.com/MakerDAO/status/1239270910810411008
            return FVal('1018008449363110619399951035')

        block_number = self.ethereum.get_blocknumber_by_time(time)
        latest_block = self.ethereum.get_latest_block_number()
        blocks_queried = 0
        counter = 1
        # Keep trying to find events that could reveal the chi to us. Go back
        # as far as MAX_BLOCKS_TO_QUERY and only then give up
        while blocks_queried < MAX_BLOCKS_TO_QUERY:
            back_from_block = max(
                MAKERDAO_POT.deployed_block,
                block_number - counter * CHI_BLOCKS_SEARCH_DISTANCE,
            )
            back_to_block = block_number - (counter - 1) * CHI_BLOCKS_SEARCH_DISTANCE
            forward_from_block = min(
                latest_block,
                block_number + (counter - 1) * CHI_BLOCKS_SEARCH_DISTANCE,
            )
            forward_to_block = min(
                latest_block,
                block_number + CHI_BLOCKS_SEARCH_DISTANCE,
            )
            back_joins, back_exits = self._get_join_exit_events(back_from_block, back_to_block)
            forward_joins, forward_exits = self._get_join_exit_events(
                from_block=forward_from_block,
                to_block=forward_to_block,
            )

            no_results = all(
                len(x) == 0 for x in (back_joins, back_exits, forward_joins, forward_exits)
            )
            if latest_block == forward_to_block and no_results:
                # if our forward querying got us to the latest block and there is
                # still no other results, then take current chi
                return self.ethereum.call_contract(
                    contract_address=MAKERDAO_POT.address,
                    abi=MAKERDAO_POT.abi,
                    method_name='chi',
                )

            if not no_results:
                # got results!
                break

            blocks_queried += 2 * CHI_BLOCKS_SEARCH_DISTANCE
            counter += 1

        if no_results:
            raise ChiRetrievalError(
                f'Found no DSR events around timestamp {time}. Cant query chi.',
            )

        # Find the closest event to the to_block number, looking both at events
        # in the blocks before and in the blocks after block_number
        found_event = None
        back_event = _find_closest_event(back_joins, back_exits, -1, operator.gt)
        forward_event = _find_closest_event(forward_joins, forward_exits, 0, operator.lt)

        if back_event and not forward_event:
            found_event = back_event
        elif forward_event and not back_event:
            found_event = forward_event
        else:
            # We have both backward and forward events, get the one closer to block number
            back_block_number = back_event['blockNumber']  # type: ignore
            forward_block_number = forward_event['blockNumber']  # type: ignore

            if block_number - back_block_number <= forward_block_number - block_number:
                found_event = back_event
            else:
                found_event = forward_event

        assert found_event, 'at this point found_event should be populated'  # helps mypy
        event_block_number = found_event['blockNumber']
        first_topic = found_event['topics'][0]

        amount = self._get_vat_join_exit_at_transaction(
            movement_type='join' if first_topic.startswith('0x049878f3') else 'exit',
            proxy_address=hex_or_bytes_to_address(found_event['topics'][1]),
            block_number=event_block_number,
            transaction_index=found_event['transactionIndex'],
        )
        if amount is None:
            raise ChiRetrievalError(
                f'Found no VAT.move events around timestamp {time}. Cant query chi.',
            )

        wad_val = hexstr_to_int(found_event['topics'][2])
        chi = FVal(amount) / FVal(wad_val)
        return chi

    def _get_dsr_account_gain_in_period(
            self,
            movements: List[DSRMovement],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> Optional[DSRGain]:
        """Get DSR gain for the account in a given period

        May raise:
        - ChiRetrievalError if we are unable to query chi at the given timestamp
        - RemoteError if etherscan is queried and there is a problem with the query
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        # First events show up ~432000 seconds after deployment
        if from_ts < POT_CREATION_TIMESTAMP:
            from_ts = Timestamp(POT_CREATION_TIMESTAMP + 432000)

        if to_ts < POT_CREATION_TIMESTAMP:
            to_ts = Timestamp(POT_CREATION_TIMESTAMP + 432000)

        from_chi = self._try_get_chi_close_to(from_ts)
        to_chi = self._try_get_chi_close_to(to_ts)
        normalized_balance = 0
        amount_in_dsr = 0
        gain_at_from_ts = ZERO
        gain_at_to_ts = ZERO
        gain_at_from_ts_found = False
        gain_at_to_ts_found = False
        last_timestamp = to_ts
        tx_hashes = []
        for m in movements:
            if not gain_at_from_ts_found and m.timestamp >= from_ts:
                gain_at_from_ts = normalized_balance * from_chi - amount_in_dsr
                gain_at_from_ts_found = True

            if not gain_at_to_ts_found and m.timestamp >= to_ts:
                gain_at_to_ts = normalized_balance * to_chi - amount_in_dsr
                gain_at_to_ts_found = True

            tx_hashes.append(m.tx_hash)
            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
                if amount_in_dsr > ZERO:
                    last_timestamp = to_ts
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance
                if FVal(amount_in_dsr).is_close(ZERO, max_diff="1e10"):
                    last_timestamp = m.timestamp

        if not gain_at_from_ts_found:
            return None

        if not gain_at_to_ts_found:
            gain_at_to_ts = normalized_balance * to_chi - amount_in_dsr

        return DSRGain(
            amount=_dsrdai_to_dai(gain_at_to_ts - gain_at_from_ts),
            from_timestamp=from_ts,
            to_timestamp=last_timestamp,
            tx_hashes=tx_hashes,
        )

    def get_dsr_gains_in_period(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[DSRGain]:
        """Get DSR gains for all accounts in a given period

        This is a best effort attempt and may also fail due to inability to find
        the required data via logs
        """
        history = self.get_historical_dsr()

        gains = []
        for account, report in history.items():
            try:
                gain = self._get_dsr_account_gain_in_period(
                    movements=report.movements,
                    from_ts=from_ts,
                    to_ts=to_ts,
                )
                if gain is not None:
                    gains.append(gain)

            except (ChiRetrievalError, RemoteError, BlockchainQueryError) as e:
                self.msg_aggregator.add_warning(
                    f'Failed to get DSR gains for {account} between '
                    f'{from_ts} and {to_ts}: {str(e)}',
                )
                continue

        return gains

    # -- Methods following the EthereumModule interface -- #
    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        super().on_account_removal(address)
        with self.lock:
            self.historical_dsr_reports.pop(address, 'None')
