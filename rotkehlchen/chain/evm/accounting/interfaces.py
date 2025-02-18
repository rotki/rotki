import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:

    from rotkehlchen.chain.evm.accounting.structures import EventsAccountantCallback
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ModuleAccountantInterface(ABC):

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
        # It's okay to call overridden reset here, since super class reset does not do anything.
        # If at any point it does we have to make sure all overridden reset() call parent
        self.reset()

    @abstractmethod
    def event_callbacks(self) -> dict[int, tuple[int, 'EventsAccountantCallback']]:
        """
        Subclasses implement this to specify callbacks that should be executed for combinations of
        type, subtype and counterparty.

        It returns a mapping of (hashed type, subtype, counterparty) to a tuple of the number of
        events processed and the logic that will process them. If the number of events
        is variable it returns -1 and the user needs to actually call the logic to get the number
        of processed events.
        """

    def reset(self) -> None:
        """Subclasses may implement this to reset state between accounting runs"""
        return None
