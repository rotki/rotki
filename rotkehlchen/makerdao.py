import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional

from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.chain.ethereum import Ethchain, address_to_bytes32
from rotkehlchen.constants.ethereum import (
    MAKERDAO_POT_ABI,
    MAKERDAO_POT_ADDRESS,
    MAKERDAO_PROXY_REGISTRY_ABI,
    MAKERDAO_PROXY_REGISTRY_ADDRESS,
    MAKERDAO_VAT_ABI,
    MAKERDAO_VAT_ADDRESS,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import ConversionError, DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_blocknumber
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import hex_or_bytes_to_int

log = logging.getLogger(__name__)


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


def _dsrdai_to_dai(value: int) -> FVal:
    """Turns a big integer that is the value of DAI in DSR into a proper DAI decimal FVal"""
    return FVal(value / 1e27 / 1e18)


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
            ethchain: Ethchain,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethchain = ethchain
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.lock = Semaphore()
        self.historical_dsr_reports: Dict[ChecksumEthAddress, DSRAccountReport] = {}

    def _get_account_proxy(self, address: ChecksumEthAddress) -> Optional[ChecksumEthAddress]:
        """Checks if a DSR proxy exists for the given address and returns it if it does

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        """
        result = self.ethchain.call_contract(
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
        """
        with self.lock:
            proxy_mappings = self.get_accounts_having_maker_proxy()
            balances = {}
            for account, proxy in proxy_mappings.items():
                guy_slice = self.ethchain.call_contract(
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
                    method_name='pie',
                    arguments=[proxy],
                )
                chi = self.ethchain.call_contract(
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
                    method_name='chi',
                )
                balance = _dsrdai_to_dai(guy_slice * chi)

                balances[account] = balance

            current_dsr = self.ethchain.call_contract(
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
        """
        arg1 = address_to_bytes32(from_address)
        arg2 = address_to_bytes32(to_address)
        argument_filters = {
            'sig': '0xbb35783b',  # move
            'arg1': arg1,  # src
            'arg2': arg2,  # dst
        }
        events = self.ethchain.get_logs(
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
        """
        movements = []
        join_normalized_balances = []
        exit_normalized_balances = []
        argument_filters = {
            'sig': '0x049878f3',  # join
            'usr': proxy,
        }
        join_events = self.ethchain.get_logs(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=8928160,  # POT creation block
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
                    timestamp=self.ethchain.get_event_timestamp(join_event),
                ),
            )

        argument_filters = {
            'sig': '0x7f8661a1',  # exit
            'usr': proxy,
        }
        exit_events = self.ethchain.get_logs(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=8928160,  # POT creation block
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
                    timestamp=self.ethchain.get_event_timestamp(exit_event),
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

        chi = self.ethchain.call_contract(
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
