import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.tools import BaseDecoderTools
from rotkehlchen.chain.starknet.types import StarknetTransaction
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.starknet_event import StarknetEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import StarknetAddress, Timestamp
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.starknet.node_inquirer import StarknetInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StarknetDecoderTools(BaseDecoderTools[StarknetTransaction, StarknetAddress, str, StarknetEvent]):  # noqa: E501
    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'StarknetInquirer',
    ) -> None:
        super().__init__(
            database=database,
            blockchain=node_inquirer.blockchain,
            address_is_exchange_fn=lambda x: None,
        )
        self.node_inquirer = node_inquirer

    def make_event(
            self,
            tx_ref: str,
            sequence_index: int,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            amount: FVal,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            address: StarknetAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> StarknetEvent:
        """A convenience function to create a StarknetEvent"""
        return StarknetEvent(
            tx_ref=tx_ref,
            sequence_index=sequence_index,
            timestamp=ts_sec_to_ms(timestamp),
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            address=address,
            extra_data=extra_data,
        )
