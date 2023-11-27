from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithGauges
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_VELODROME

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS


class VelodromeBalances(ProtocolWithGauges):
    """
    Query balances in Velodrome gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'EvmNodeInquirer',
            chain_id: 'CHAIN_IDS_WITH_BALANCE_PROTOCOLS',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            chain_id=chain_id,
            counterparty=CPT_VELODROME,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        return event.address
