import importlib
import logging
import pkgutil
from contextlib import suppress
from types import ModuleType
from typing import TYPE_CHECKING

from rotkehlchen.errors.misc import ModuleLoadingError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.user_messages import MessagesAggregator

from .structures import EventsAccountantCallback

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

    from .interfaces import ModuleAccountantInterface


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EVMAccountingAggregator:
    """This is a class meant to aggregate accountants for modules of EVM decoders

    It's supposed to be subclassed for each different evm network. The reason for
    subclassing is to allow custom functionality for each chain. This is not yet
    implemented/used but it was thought good to start like that as changing later
    would be a hassle.
    """
    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            msg_aggregator: MessagesAggregator,
            modules_path: str,
    ) -> None:
        self.node_inquirer = node_inquirer
        self.msg_aggregator = msg_aggregator
        self.accountants: dict[str, ModuleAccountantInterface] = {}
        self.modules_path = modules_path
        self.initialize_all_accountants()

    def _recursively_initialize_accountants(
            self, package: str | ModuleType,
    ) -> None:
        modules_prefix_length = len(self.modules_path) + 1  # +1 is for '.'
        if isinstance(package, str):
            package = importlib.import_module(package)
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            if full_name == __name__ or is_pkg is False:
                continue  # skip

            if is_pkg:
                submodule = None
                with suppress(ModuleNotFoundError):
                    submodule = importlib.import_module(full_name + '.accountant')

                if submodule is not None:
                    class_name = full_name[modules_prefix_length:].translate({ord('.'): None})
                    submodule_accountant = getattr(submodule, f'{class_name.capitalize()}Accountant', None)  # noqa: E501

                    if submodule_accountant:
                        if class_name in self.accountants:
                            raise ModuleLoadingError(f'Accountant with name {class_name} already loaded')  # noqa: E501

                        self.accountants[class_name] = submodule_accountant(
                            node_inquirer=self.node_inquirer,
                            msg_aggregator=self.msg_aggregator,
                        )

                self._recursively_initialize_accountants(full_name)

    def initialize_all_accountants(self) -> None:
        """Recursively check all submodules to get all accountants and initialize them"""
        self._recursively_initialize_accountants(self.modules_path)

    def get_accounting_callbacks(self) -> dict[int, tuple[int, EventsAccountantCallback]]:
        """
        Iterate through loaded accountants and get accounting callbacks for each event type.
        It returns a mapping of event type identifier to a tuple where the fist element is the
        number of events processed (-1 if it is variable) and the callback that processes
        those events.
        """
        result = {}
        for accountant in self.accountants.values():
            result.update(accountant.event_callbacks())

        return result

    def reset(self) -> None:
        """Reset the state of all initialized submodule accountants"""
        for accountant in self.accountants.values():
            accountant.reset()


class EVMAccountingAggregators:
    """
    This is just a convenience class to group together AccountingAggregators from multiple chains
    """

    def __init__(self, aggregators: list[EVMAccountingAggregator]) -> None:
        self.aggregators = aggregators

    def get_accounting_callbacks(self) -> dict[int, tuple[int, EventsAccountantCallback]]:
        """
        Iterate through loaded accountants and get accounting callbacks for each event type
        It returns a mapping of event type identifier to a tuple where the fist element is the
        number of events processed (-1 if it is variable) and the callback that processes
        those events.
        """
        result = {}
        for aggregator in self.aggregators:
            result.update(aggregator.get_accounting_callbacks())

        return result

    def reset(self) -> None:
        """Reset the state of all initialized submodule accountants"""
        for aggregator in self.aggregators:
            aggregator.reset()
