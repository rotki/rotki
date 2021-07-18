import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Union

from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.accounting.structures import AssetBalance, Balance, DefiEvent, DefiEventType
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.ethereum import MAKERDAO_DAI_JOIN, MAKERDAO_POT
from rotkehlchen.errors import ConversionError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_or_use_default
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hexstr_to_int, ts_now

from .common import MakerdaoCommon
from .constants import MAKERDAO_REQUERY_PERIOD, RAD, RAY

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

    # -- Methods following the EthereumModule interface -- #
    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        super().on_account_removal(address)
        with self.lock:
            self.historical_dsr_reports.pop(address, 'None')
