import logging
import operator
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.chain.ethereum.manager import EthereumManager, address_to_bytes32
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.ethereum import (
    MAKERDAO_POT_ABI,
    MAKERDAO_POT_ADDRESS,
    MAKERDAO_PROXY_REGISTRY_ABI,
    MAKERDAO_PROXY_REGISTRY_ADDRESS,
    MAKERDAO_VAT_ABI,
    MAKERDAO_VAT_ADDRESS,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import (
    BlockchainQueryError,
    ConversionError,
    DeserializationError,
    RemoteError,
)
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_blocknumber
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_int

log = logging.getLogger(__name__)

POT_CREATION_BLOCK = 8928160
POT_CREATION_TIMESTAMP = 1573672721
CHI_BLOCKS_SEARCH_DISTANCE = 250  # Blocks per call query per side (before/after)
MAX_BLOCKS_TO_QUERY = 346000  # query about a month's worth of blocks in each side before giving up


class ChiRetrievalError(Exception):
    pass


def hex_or_bytes_to_address(value: Union[bytes, str]) -> ChecksumEthAddress:
    """Turns a 32bit bytes/HexBytes or a hexstring into an address

    May raise:
    - ConversionError if it can't convert a value to an int or if an unexpected
    type is given.
    """
    if isinstance(value, bytes):
        hexstr = value.hex()
    else:
        hexstr = value

    return ChecksumEthAddress(to_checksum_address('0x' + hexstr[26:]))


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
            try:
                join_number = deserialize_blocknumber(found_event['blockNumber'])
                exit_number = deserialize_blocknumber(exit_events[index]['blockNumber'])
            except DeserializationError as e:
                msg = f'Error at reading DSR drip event block number. {str(e)}'
                raise ChiRetrievalError(msg)

            if comparison(exit_number, join_number):
                found_event = exit_events[index]
        else:
            found_event = exit_events[index]

    return found_event


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMovement:
    movement_type: Literal['deposit', 'withdrawal']
    address: ChecksumEthAddress
    normalized_balance: int
    gain_so_far: int = field(init=False)
    amount: int
    block_number: int
    timestamp: Timestamp


class DSRCurrentBalances(NamedTuple):
    balances: Dict[ChecksumEthAddress, FVal]
    # The percentage of the current DSR. e.g. 8% would be 8.00
    current_dsr: FVal


class DSRAccountReport(NamedTuple):
    movements: List[DSRMovement]
    gain_so_far: int


def _dsrdai_to_dai(value: Union[int, FVal]) -> FVal:
    """Turns a big integer that is the value of DAI in DSR into a proper DAI decimal FVal"""
    return FVal(value / FVal(1e27) / FVal(1e18))


def serialize_dsr_reports(
        reports: Dict[ChecksumEthAddress, DSRAccountReport],
) -> Dict[ChecksumEthAddress, Dict[str, Any]]:
    """Serializes a DSR Report into a dict.

    Turns DAI into proper decimals and omits fields we don't need to export
    """
    result = {}
    for account, report in reports.items():
        serialized_report = {
            'gain_so_far': str(_dsrdai_to_dai(report.gain_so_far)),
            'movements': [],
        }
        for movement in report.movements:
            serialized_movement = {
                'movement_type': movement.movement_type,
                'gain_so_far': str(_dsrdai_to_dai(movement.gain_so_far)),
                'amount': str(_dsrdai_to_dai(movement.amount)),
                'block_number': movement.block_number,
                'timestamp': movement.timestamp,
            }
            serialized_report['movements'].append(serialized_movement)  # type: ignore
        result[account] = serialized_report

    return result


class MakerDAO(EthereumModule):
    """Class to manage MakerDAO related stuff such as DSR and CDPs/Vaults"""

    def __init__(
            self,
            ethereum_manager: EthereumManager,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.lock = Semaphore()
        self.historical_dsr_reports: Dict[ChecksumEthAddress, DSRAccountReport] = {}

    def _get_account_proxy(self, address: ChecksumEthAddress) -> Optional[ChecksumEthAddress]:
        """Checks if a DSR proxy exists for the given address and returns it if it does

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        result = self.ethereum.call_contract(
            contract_address=MAKERDAO_PROXY_REGISTRY_ADDRESS,
            abi=MAKERDAO_PROXY_REGISTRY_ABI,
            method_name='proxies',
            arguments=[address],
        )
        if int(result, 16) != 0:
            return to_checksum_address(result)
        return None

    def get_accounts_having_maker_proxy(self) -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        """Returns a mapping of accounts that have DSR proxies to their proxies

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        """
        mapping = {}
        accounts = self.database.get_blockchain_accounts()
        for account in accounts.eth:
            proxy_result = self._get_account_proxy(account)
            if proxy_result:
                mapping[account] = proxy_result

        return mapping

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
            proxy_mappings = self.get_accounts_having_maker_proxy()
            balances = {}
            for account, proxy in proxy_mappings.items():
                guy_slice = self.ethereum.call_contract(
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
                    method_name='pie',
                    arguments=[proxy],
                )
                chi = self.ethereum.call_contract(
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
                    method_name='chi',
                )
                balance = _dsrdai_to_dai(guy_slice * chi)

                balances[account] = balance

            current_dsr = self.ethereum.call_contract(
                contract_address=MAKERDAO_POT_ADDRESS,
                abi=MAKERDAO_POT_ABI,
                method_name='dsr',
            )

            # Calculation is from here:
            # https://docs.makerdao.com/smart-contract-modules/rates-module#a-note-on-setting-rates
            current_dsr_percentage = ((FVal(current_dsr / 1e27) ** 31622400) % 1) * 100
            result = DSRCurrentBalances(balances=balances, current_dsr=current_dsr_percentage)

        return result

    def _get_vat_move_event_value(
            self,
            from_address: ChecksumEthAddress,
            to_address: ChecksumEthAddress,
            block_number: int,
            transaction_index: int,
    ) -> Optional[int]:
        """Returns values in DAI that were moved from to address at a block number and tx index

        Returns None if no value was found of if there was an error with conversion.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        arg1 = address_to_bytes32(from_address)
        arg2 = address_to_bytes32(to_address)
        argument_filters = {
            'sig': '0xbb35783b',  # move
            'arg1': arg1,  # src
            'arg2': arg2,  # dst
        }
        events = self.ethereum.get_logs(
            contract_address=MAKERDAO_VAT_ADDRESS,
            abi=MAKERDAO_VAT_ABI,
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
                    value = hex_or_bytes_to_int(event['topics'][3])
                    break
                except ConversionError:
                    value = None
        return value

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
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=POT_CREATION_BLOCK,
        )
        for join_event in join_events:
            try:
                wad_val = hex_or_bytes_to_int(join_event['topics'][2])
            except ConversionError as e:
                msg = f'Error at reading DSR join event topics. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            join_normalized_balances.append(wad_val)

            # and now get the deposit amount
            try:
                block_number = deserialize_blocknumber(join_event['blockNumber'])
            except DeserializationError as e:
                msg = f'Error at reading DSR join event block number. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            dai_value = self._get_vat_move_event_value(
                from_address=proxy,
                to_address=MAKERDAO_POT_ADDRESS,
                block_number=block_number,
                transaction_index=join_event['transactionIndex'],
            )
            if not dai_value:
                self.msg_aggregator.add_error(
                    'Did not find corresponding vat.move event for pot join. Skipping ...',
                )
                continue

            movements.append(
                DSRMovement(
                    movement_type='deposit',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    block_number=deserialize_blocknumber(join_event['blockNumber']),
                    timestamp=self.ethereum.get_event_timestamp(join_event),
                ),
            )

        argument_filters = {
            'sig': '0x7f8661a1',  # exit
            'usr': proxy,
        }
        exit_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=POT_CREATION_BLOCK,
        )
        for exit_event in exit_events:
            try:
                wad_val = hex_or_bytes_to_int(exit_event['topics'][2])
            except ConversionError as e:
                msg = f'Error at reading DSR exit event topics. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue
            exit_normalized_balances.append(wad_val)

            try:
                block_number = deserialize_blocknumber(exit_event['blockNumber'])
            except DeserializationError as e:
                msg = f'Error at reading DSR exit event block number. {str(e)}. Skipping event...'
                self.msg_aggregator.add_error(msg)
                continue

            # and now get the withdrawal amount
            dai_value = self._get_vat_move_event_value(
                from_address=MAKERDAO_POT_ADDRESS,
                to_address=proxy,
                block_number=block_number,
                transaction_index=exit_event['transactionIndex'],
            )
            if not dai_value:
                self.msg_aggregator.add_error(
                    'Did not find corresponding vat.move event for pot exit. Skipping ...',
                )
                continue

            movements.append(
                DSRMovement(
                    movement_type='withdrawal',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    block_number=deserialize_blocknumber(exit_event['blockNumber']),
                    timestamp=self.ethereum.get_event_timestamp(exit_event),
                ),
            )

        normalized_balance = 0
        amount_in_dsr = 0
        movements.sort(key=lambda x: x.block_number)

        for m in movements:
            current_chi = FVal(m.amount) / FVal(m.normalized_balance)
            gain_so_far = normalized_balance * current_chi - amount_in_dsr
            m.gain_so_far = gain_so_far.to_int(exact=False)
            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance

        chi = self.ethereum.call_contract(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            method_name='chi',
        )
        normalized_balance = normalized_balance * chi
        amount_in_dsr = amount_in_dsr
        gain = normalized_balance - amount_in_dsr

        return DSRAccountReport(movements=movements, gain_so_far=gain)

    def get_historical_dsr(self) -> Dict[ChecksumEthAddress, DSRAccountReport]:
        with self.lock:
            proxy_mappings = self.get_accounts_having_maker_proxy()
            reports = {}
            for account, proxy in proxy_mappings.items():
                report = self._historical_dsr_for_account(account, proxy)
                reports[account] = report

        return reports

    def _get_join_exit_events(
            self,
            from_block: int,
            to_block: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        join_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            event_name='LogNote',
            argument_filters={'sig': '0x049878f3'},  # join
            from_block=from_block,
            to_block=to_block,
        )
        exit_events = self.ethereum.get_logs(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
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
        block_number = self.ethereum.etherscan.get_blocknumber_by_time(time)
        if self.ethereum.connected:
            latest_block = self.ethereum.web3.eth.blockNumber
        else:
            latest_block = self.ethereum.query_eth_highest_block()

        blocks_queried = 0
        counter = 1
        # Keep trying to find events that could reveal the chi to us. Go back
        # as far as MAX_BLOCKS_TO_QUERY and only then give up
        while blocks_queried < MAX_BLOCKS_TO_QUERY:
            back_from_block = max(
                POT_CREATION_BLOCK,
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
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
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
            try:
                back_block_number = deserialize_blocknumber(back_event['blockNumber'])  # type: ignore  # noqa: E501
                forward_block_number = deserialize_blocknumber(forward_event['blockNumber'])  # type: ignore  # noqa: E501
            except DeserializationError as e:
                msg = f'Error at reading DSR drip event block number. {str(e)}'
                raise ChiRetrievalError(msg)

            if block_number - back_block_number <= forward_block_number - block_number:
                found_event = back_event
            else:
                found_event = forward_event

        assert found_event, 'at this point found_event should be populated'  # helps mypy
        event_block_number = deserialize_blocknumber(found_event['blockNumber'])
        first_topic = found_event['topics'][0]
        if isinstance(first_topic, bytes):
            first_topic = first_topic.hex()

        if first_topic.startswith('0x049878f3'):  # join
            from_address = hex_or_bytes_to_address(found_event['topics'][1])
            to_address = MAKERDAO_POT_ADDRESS
        else:
            from_address = MAKERDAO_POT_ADDRESS
            to_address = hex_or_bytes_to_address(found_event['topics'][1])

        amount = self._get_vat_move_event_value(
            from_address=from_address,
            to_address=to_address,
            block_number=event_block_number,
            transaction_index=found_event['transactionIndex'],
        )
        if not amount:
            raise ChiRetrievalError(
                f'Found no VAT.move events around timestamp {time}. Cant query chi.',
            )

        wad_val = hex_or_bytes_to_int(found_event['topics'][2])
        chi = FVal(amount) / FVal(wad_val)
        return chi

    def _get_dsr_account_gain_in_period(
            self,
            movements: List[DSRMovement],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> FVal:
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
        for m in movements:
            if not gain_at_from_ts_found and m.timestamp >= from_ts:
                gain_at_from_ts = normalized_balance * from_chi - amount_in_dsr
                gain_at_from_ts_found = True

            if not gain_at_to_ts_found and m.timestamp >= to_ts:
                gain_at_to_ts = normalized_balance * to_chi - amount_in_dsr
                gain_at_to_ts_found = True

            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance

        if not gain_at_from_ts_found:
            return ZERO
        if not gain_at_to_ts_found:
            gain_at_to_ts = normalized_balance * to_chi - amount_in_dsr

        return _dsrdai_to_dai(gain_at_to_ts - gain_at_from_ts)

    def get_dsr_gains_in_period(self, from_ts: Timestamp, to_ts: Timestamp) -> FVal:
        """Get DSR gains for all accounts in a given period

        This is a best effort attempt and may also fail due to inability to find
        the required data via logs
        """
        with self.lock:
            history = self.historical_dsr_reports

        gain = ZERO
        for account, report in history.items():
            try:
                gain += self._get_dsr_account_gain_in_period(
                    movements=report.movements,
                    from_ts=from_ts,
                    to_ts=to_ts,
                )
            except (ChiRetrievalError, RemoteError, BlockchainQueryError) as e:
                self.msg_aggregator.add_warning(
                    f'Failed to get DSR gains for {account} between '
                    f'{from_ts} and {to_ts}: {str(e)}',
                )
                continue

        return gain

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        self.historical_dsr_reports = self.get_historical_dsr()

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        with self.lock:
            proxy = self._get_account_proxy(address)
            if not proxy:
                return
            report = self._historical_dsr_for_account(address, proxy)
            self.historical_dsr_reports[address] = report

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        with self.lock:
            self.historical_dsr_reports.pop(address, 'None')
