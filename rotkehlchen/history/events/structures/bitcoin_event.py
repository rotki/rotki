import logging
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.chain.bitcoin.bch.constants import BCH_GROUP_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.btc.constants import BTC_GROUP_IDENTIFIER_PREFIX
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import BTCAddress, BTCTxId, FVal, Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.history.events.structures.types import (
        HistoryEventSubType,
        HistoryEventType,
    )

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitcoinEvent(OnchainEvent[BTCTxId, BTCAddress]):
    """A bitcoin or bitcoin cash event.

    Unlike the other chains a single event can have any number of counterparty addresses,
    since a transaction moving value between many addresses has no one-to-one mapping
    between the two sides. They live in `bitcoin_events_addresses` rather than in the
    `address` column of chain_events_info, which stays unused here.

    `counterparty_addresses` only carries them from decoding to the write. It is not read
    back with the event and so takes no part in equality, the same way the metadata
    attribute it replaces didn't.
    """

    def __init__(
            self,
            tx_ref: BTCTxId,
            sequence_index: int,
            timestamp: TimestampMS,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: Asset,
            amount: FVal,
            location: Literal[Location.BITCOIN, Location.BITCOIN_CASH] = Location.BITCOIN,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            address: BTCAddress | None = None,
            counterparty_addresses: list[BTCAddress] | None = None,
            extra_data: dict[str, Any] | None = None,
            group_identifier: str | None = None,
    ) -> None:
        super().__init__(
            tx_ref=tx_ref,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            identifier=identifier,
            counterparty=counterparty,
            address=address,
            extra_data=extra_data,
            group_identifier=group_identifier,
        )
        self.counterparty_addresses = counterparty_addresses

    @staticmethod
    def _calculate_group_identifier(tx_ref: BTCTxId, location: Location) -> str:
        return (
            BTC_GROUP_IDENTIFIER_PREFIX if location == Location.BITCOIN
            else BCH_GROUP_IDENTIFIER_PREFIX
        ) + str(tx_ref)

    @staticmethod
    def _serialize_tx_ref_for_db(tx_ref: BTCTxId) -> bytes:
        """May raise DeserializationError if the tx id is not valid hex."""
        try:
            return bytes.fromhex(tx_ref)
        except ValueError as e:
            raise DeserializationError(f'Invalid bitcoin transaction id {tx_ref}') from e

    @staticmethod
    def _deserialize_tx_ref(tx_ref_data: Any) -> BTCTxId:
        if isinstance(tx_ref_data, bytes):
            return BTCTxId(tx_ref_data.hex())

        return BTCTxId(str(tx_ref_data))

    @staticmethod
    def deserialize_address(address_data: Any) -> BTCAddress:
        return BTCAddress(address_data)

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.BITCOIN_EVENT

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'self.tx_ref={self.tx_ref!s}',
            f'{self.counterparty_addresses=}',
        ]
        return f'{self.__class__.__name__}({", ".join(fields)})'
