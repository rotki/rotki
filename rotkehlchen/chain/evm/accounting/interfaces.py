import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Iterator, Literal

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.structures.types import HistoryEventType
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.accounting.structures.base import HistoryBaseEntry
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

    from .structures import TxEventSettings

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:  # pylint: disable=no-self-use  # noqa: E501
        """
        Subclasses implement this to specify rules/settings for their created events
        """
        ...

    def reset(self) -> None:  # pylint: disable=no-self-use
        """Subclasses may implement this to reset state between accounting runs"""
        return None


class DepositableAccountantInterface(ModuleAccountantInterface):
    """
    Interface for protocols that allow to deposit multiple tokens in exchange for a token
    representing the position in the pool. Examples are:
    - Curve
    - Balancer
    """

    def _process_deposit_or_withdrawal(
            self,
            pot: 'AccountingPot',
            event: 'HistoryBaseEntry',
            other_events: Iterator['HistoryBaseEntry'],
    ) -> None:
        """
        Process deposits and withdrawals from protocols that allow to deposit multiple assets
        in return for a wrapped token. There are multiple events that we have to consume from
        the iterator.

        The receive wrapped event needs to have in the extra data field a key `deposit_events_num`
        marking the number of events to consume.
        The return wrapped event needs to have the key `withdrawal_events_num` with the number
        of events in the return event.
        """
        method: Literal['acquisition', 'spend']
        if event.event_type == HistoryEventType.RECEIVE:
            # Pool token is received, which means it is a deposit
            events_to_consume = event.extra_data.get('deposit_events_num', None) if event.extra_data is not None else None  # noqa: E501
            method = 'spend'
        else:  # Withdrawal
            events_to_consume = event.extra_data.get('withdrawal_events_num', None) if event.extra_data is not None else None  # noqa: E501
            method = 'acquisition'

        if events_to_consume is None:
            log.debug(
                f'Could not find the number of events to consume for a {self.name} '
                f'deposit/withdrawal transaction {event.serialized_event_identifier}',
            )
            return

        # Consume the events
        for idx in range(events_to_consume):
            next_event = next(other_events, None)
            if next_event is None:
                log.debug(f'Could not consume event nr. {idx} for {event.counterparty} deposit/withdrawal')  # noqa: E501
                return

            if next_event.balance.amount == ZERO:
                continue

            pot.add_asset_change_event(
                method=method,
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=next_event.notes if next_event.notes else '',
                location=next_event.location,
                timestamp=next_event.get_timestamp_in_sec(),
                asset=next_event.asset,
                amount=next_event.balance.amount,
                taxable=False,  # Deposits and withdrawals are not taxable
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                extra_data={'tx_hash': next_event.serialized_event_identifier},
            )

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the protocol that uses this interface"""
        ...
