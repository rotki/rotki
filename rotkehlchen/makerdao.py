import logging
from typing import Dict, List, NamedTuple

from dataclasses import dataclass, field
from eth_utils.address import to_checksum_address
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.constants.ethereum import (
    MAKERDAO_POT_ABI,
    MAKERDAO_POT_ADDRESS,
    MAKERDAO_PROXY_REGISTRY_ABI,
    MAKERDAO_PROXY_REGISTRY_ADDRESS,
    MAKERDAO_VAT_ABI,
    MAKERDAO_VAT_ADDRESS,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.ethchain import Ethchain, address_to_bytes32
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.utils.interfaces import EthereumModule

log = logging.getLogger(__name__)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DSRMovement:
    movement_type: Literal['deposit', 'withdrawal']
    address: ChecksumEthAddress
    normalized_balance: int
    gain_so_far: int = field(init=False)
    amount: int
    block_number: int


class DSRAccountReport(NamedTuple):
    movements: List[DSRMovement]
    gain_so_far: int


class MakerDAO(EthereumModule):
    """Class to manage MakerDAO related stuff such as DSR and CDPs/Vaults"""

    def __init__(self, ethchain: Ethchain, database: DBHandler) -> None:
        self.ethchain = ethchain
        self.database = database
        self.lock = Semaphore()

    def _get_account_proxy(self, address: ChecksumEthAddress) -> ChecksumEthAddress:
        """Checks if a DSR proxy exists for the given address and returns it if it does"""
        result = self.ethchain.check_contract(
            contract_address=MAKERDAO_PROXY_REGISTRY_ADDRESS,
            abi=MAKERDAO_PROXY_REGISTRY_ABI,
            method_name='proxies',
            arguments=[address],
        )
        if int(result, 16) != 0:
            return to_checksum_address(result)
        return None

    def get_accounts_having_maker_proxy(self) -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        mapping = {}
        accounts = self.database.get_blockchain_accounts()
        for account in accounts.eth:
            proxy_result = self._get_account_proxy(account)
            if proxy_result:
                mapping[account] = proxy_result

        return mapping

    def get_current_dsr(self) -> Dict[ChecksumEthAddress, FVal]:
        with self.lock:
            proxy_mappings = self.get_accounts_having_maker_proxy()
            balances = {}
            for account, proxy in proxy_mappings.items():
                guy_slice = self.ethchain.check_contract(
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
                    method_name='pie',
                    arguments=[proxy],
                )
                chi = self.ethchain.check_contract(
                    contract_address=MAKERDAO_POT_ADDRESS,
                    abi=MAKERDAO_POT_ABI,
                    method_name='chi',
                )
                balance = FVal((guy_slice * chi) / (1e27) / (1e18))
                balances[account] = balance

        return balances

    def _get_vat_move_event_value(
            self,
            from_address: ChecksumEthAddress,
            to_address: ChecksumEthAddress,
            block_number: int,
            transaction_index: int
    ) -> int:
        """Returns values in DAI that were moved from to address at a block number and tx index"""
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
                    log.error(
                        'Mistaken assumption: There is multiple vat.move events for '
                        'the same transaction'
                    )
                bytes_val = event['topics'][3]
                value = int.from_bytes(bytes_val, byteorder='big', signed=False)
        return value

    def _historical_dsr_for_account(self, account, proxy) -> DSRAccountReport:
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
            bytes_val = join_event['topics'][2]
            wad_val = int.from_bytes(bytes_val, byteorder='big', signed=False)
            join_normalized_balances.append(wad_val)

            # and now get the deposit amount
            dai_value = self._get_vat_move_event_value(
                from_address=proxy,
                to_address=MAKERDAO_POT_ADDRESS,
                block_number=join_event['blockNumber'],
                transaction_index=join_event['transactionIndex'],
            )
            movements.append(
                DSRMovement(
                    movement_type='deposit',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    block_number=join_event['blockNumber'],
                )
            )

        argument_filters = {
            'sig': '0x7f8661a1',  # exit
            'usr': proxy,  # join
        }
        exit_events = self.ethchain.get_logs(
            contract_address=MAKERDAO_POT_ADDRESS,
            abi=MAKERDAO_POT_ABI,
            event_name='LogNote',
            argument_filters=argument_filters,
            from_block=8928160,  # POT creation block
        )
        for exit_event in exit_events:
            bytes_val = exit_event['topics'][2]

            wad_val = int.from_bytes(bytes_val, byteorder='big', signed=False)
            exit_normalized_balances.append(wad_val)

            # and now get the withdrawals amounts
            dai_value = self._get_vat_move_event_value(
                from_address=MAKERDAO_POT_ADDRESS,
                to_address=proxy,
                block_number=exit_event['blockNumber'],
                transaction_index=exit_event['transactionIndex'],
            )
            movements.append(
                DSRMovement(
                    movement_type='withdrawal',
                    address=account,
                    normalized_balance=wad_val,
                    amount=dai_value,
                    block_number=exit_event['blockNumber'],
                )
            )

        normalized_balance = 0
        amount_in_dsr = 0
        movements.sort(key=lambda x: x.block_number)

        for m in movements:
            current_chi = FVal(m.amount) / FVal(m.normalized_balance)
            gain_so_far = normalized_balance * current_chi - amount_in_dsr
            m.gain_so_far = gain_so_far
            if m.movement_type == 'deposit':
                normalized_balance += m.normalized_balance
                amount_in_dsr += m.amount
            else:  # withdrawal
                amount_in_dsr -= m.amount
                normalized_balance -= m.normalized_balance

        chi = self.ethchain.check_contract(
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
            log.debug('historical dsr 1')
            proxy_mappings = self.get_accounts_having_maker_proxy()
            reports = {}
            for account, proxy in proxy_mappings.items():
                log.debug('historical dsr 2')
                report = self._historical_dsr_for_account(account, proxy)
                reports[account] = report

        return reports

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        self.get_historical_dsr()

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        with self.lock:
            proxy = self._get_account_proxy(address)
            if not proxy:
                return
            report = self._historical_dsr_for_account(address, proxy)

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
