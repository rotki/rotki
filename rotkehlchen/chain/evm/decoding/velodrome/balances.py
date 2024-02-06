from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.interfaces.balances import (
    PROTOCOLS_WITH_BALANCES,
    ProtocolWithGauges,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress


if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


class VelodromeLikeBalances(ProtocolWithGauges):
    """
    Query balances in Velodrome-like gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'OptimismInquirer | BaseInquirer',
            counterparty: PROTOCOLS_WITH_BALANCES,
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            counterparty=counterparty,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address
