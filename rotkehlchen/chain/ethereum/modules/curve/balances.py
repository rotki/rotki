from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithGauges
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


class CurveBalances(ProtocolWithGauges):
    """
    Query balances in Curve gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(self, database: DBHandler, evm_inquirer: 'EvmNodeInquirer'):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            counterparty=CPT_CURVE,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address
