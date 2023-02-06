from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

    from .structures import TxEventSettings


class ModuleAccountantInterface(metaclass=ABCMeta):

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',  # pylint: disable=unused-argument
            msg_aggregator: 'MessagesAggregator',  # pylint: disable=unused-argument
    ) -> None:
        """This is the evm module accountant interface. All module accountants
        should implement it

        To have smaller objects and since few decoders use most of the given objects
        we do not save anything here at the moment, but instead let it up to the individual
        decoder to choose what to keep"""
        # It's okay to call overriden reset here, since super class reset does not do anything.
        # If at any point it does we have to make sure all overriden reset() call parent
        self.reset()

    @abstractmethod
    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """
        Subclasses implement this to specify rules/settings for their created events
        """

    def reset(self) -> None:
        """Subclasses may implement this to reset state between accounting runs"""
        return None
