import importlib
import logging
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, Dict, Union

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.constants import MODULES_PACKAGE, MODULES_PREFIX_LENGTH
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.errors.misc import ModuleLoadingError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

from .structures import TxEventSettings

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.ethereum.manager import EthereumManager

    from .interfaces import ModuleAccountantInterface


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EVMAccountingAggregator():

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum_manager = ethereum_manager
        self.msg_aggregator = msg_aggregator
        self.accountants: Dict[str, 'ModuleAccountantInterface'] = {}
        self.initialize_all_accountants()

    def _recursively_initialize_accountants(
            self, package: Union[str, ModuleType],
    ) -> None:
        if isinstance(package, str):
            package = importlib.import_module(package)
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            if full_name == __name__:
                continue  # skip -- this is this source file

            if is_pkg:
                submodule = importlib.import_module(full_name)
                class_name = full_name[MODULES_PREFIX_LENGTH:].translate({ord('.'): None})
                submodule_accountant = getattr(submodule, f'{class_name.capitalize()}Accountant', None)  # noqa: E501

                if submodule_accountant:
                    if class_name in self.accountants:
                        raise ModuleLoadingError(f'Accountant with name {class_name} already loaded')  # noqa: E501
                    self.accountants[class_name] = submodule_accountant(
                        ethereum_manager=self.ethereum_manager,
                        msg_aggregator=self.msg_aggregator,
                    )

                self._recursively_initialize_accountants(full_name)

    def initialize_all_accountants(self) -> None:
        """Recursively check all submodules to get all accountants and initialize them"""
        self._recursively_initialize_accountants(MODULES_PACKAGE)

    def get_accounting_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:
        """Iterate through loaded accountants and get accounting settings for each event type"""
        result = {}
        for accountant in self.accountants.values():
            result.update(accountant.event_settings(pot))

        # Also add the default settings
        gas_key = str(HistoryEventType.SPEND) + '__' + str(HistoryEventSubType.FEE) + '__' + CPT_GAS  # noqa: E501
        result[gas_key] = TxEventSettings(
            taxable=pot.settings.include_gas_costs,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            take=1,
            method='spend',
        )
        spend_key = str(HistoryEventType.SPEND) + '__' + str(HistoryEventSubType.NONE)
        result[spend_key] = TxEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            take=1,
            method='spend',
        )
        receive_key = str(HistoryEventType.RECEIVE) + '__' + str(HistoryEventSubType.NONE)
        result[receive_key] = TxEventSettings(
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
            take=1,
            method='acquisition',
        )
        deposit_key = str(HistoryEventType.DEPOSIT) + '__' + str(HistoryEventSubType.NONE)
        result[deposit_key] = TxEventSettings(
            taxable=False,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=False,
            take=1,
            method='spend',
        )
        withdraw_key = str(HistoryEventType.WITHDRAWAL) + '__' + str(HistoryEventSubType.NONE)
        result[withdraw_key] = TxEventSettings(
            taxable=False,
            count_entire_amount_spend=False,
            count_cost_basis_pnl=False,
            take=1,
            method='acquisition',
        )
        return result

    def reset(self) -> None:
        """Reset the state of all initialized submodule accountants"""
        for accountant in self.accountants.values():
            accountant.reset()
