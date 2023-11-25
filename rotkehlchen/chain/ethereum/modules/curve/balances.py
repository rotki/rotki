from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithGauges
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_CURVE

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS


class CurveBalances(ProtocolWithGauges):
    """
    Query balances in Curve gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(
            self, database: DBHandler,
            evm_inquirer: 'EvmNodeInquirer',
            chain_id: 'CHAIN_IDS_WITH_BALANCE_PROTOCOLS',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            chain_id=chain_id,
            counterparty=CPT_CURVE,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address
