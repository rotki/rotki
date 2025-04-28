from typing import TYPE_CHECKING, Any, Literal, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_optional
from rotkehlchen.types import EVMTxHash, Location, TimestampMS, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import timestamp_to_date, ts_ms_to_sec

from .evm_event import EvmEvent, EvmProduct
from .swap import SwapEvent

if TYPE_CHECKING:
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.types import EVM_EVENT_DB_TUPLE_READ
    from rotkehlchen.types import ChecksumEvmAddress


class EvmSwapEvent(EvmEvent, SwapEvent):

    def __init__(
            self,
            tx_hash: EVMTxHash,
            sequence_index: int,
            timestamp: TimestampMS,
            location: Location,
            event_subtype: Literal[
                HistoryEventSubType.SPEND,
                HistoryEventSubType.RECEIVE,
                HistoryEventSubType.FEE,
            ],
            asset: Asset,
            amount: 'FVal',
            event_type: Literal[
                HistoryEventType.TRADE,
                HistoryEventType.MULTI_TRADE,
            ] = HistoryEventType.TRADE,
            location_label: str | None = None,
            notes: str | None = None,
            identifier: int | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: 'ChecksumEvmAddress | None' = None,
            extra_data: dict[str, Any] | None = None,
            event_identifier: str | None = None,
    ):
        """Combines EvmEvent with SwapEvent to represent evm swaps."""
        super().__init__(
            tx_hash=tx_hash,
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
            product=product,
            address=address,
            extra_data=extra_data,
            event_identifier=event_identifier,
        )

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.EVM_SWAP_EVENT

    @classmethod
    def deserialize_from_db(cls: type['EvmSwapEvent'], entry: tuple) -> 'EvmSwapEvent':
        """Deserialize a EvmSwapEvent DB tuple.
        May raise:
        - DeserializationError
        - UnknownAsset
        But these exceptions shouldn't normally happen since
        the data from the db should already be correct.
        """
        entry = cast('EVM_EVENT_DB_TUPLE_READ', entry)
        amount = deserialize_fval(entry[7], 'amount', 'evm swap event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            sequence_index=entry[2],
            timestamp=TimestampMS(entry[3]),
            location=Location.deserialize_from_db(entry[4]),
            location_label=entry[5],
            asset=Asset(entry[6]).check_existence(),
            amount=amount,
            notes=entry[8] or None,
            event_type=HistoryEventType.deserialize(entry[9]),  # type: ignore  # event type and subtype should always be correct from the DB
            event_subtype=HistoryEventSubType.deserialize(entry[10]),  # type: ignore
            extra_data=cls.deserialize_extra_data(entry=entry, extra_data=entry[11]),
            tx_hash=deserialize_evm_tx_hash(entry[12]),
            counterparty=entry[13],
            product=EvmProduct.deserialize(entry[14]) if entry[14] is not None else None,
            address=deserialize_optional(input_val=entry[15], fn=string_to_evm_address),
        )

    def serialize(self) -> dict[str, Any]:
        """Serialize the event for api."""
        return EvmEvent.serialize(self)

    @classmethod
    def deserialize(cls: type['EvmSwapEvent'], data: dict[str, Any]) -> 'EvmSwapEvent':
        try:
            return cls(
                **cls._deserialize_swap_data(
                    base_data=(base_data := cls._deserialize_base_history_data(data)),
                ),
                tx_hash=deserialize_evm_tx_hash(data['tx_hash']),
                sequence_index=base_data['sequence_index'],
                counterparty=deserialize_optional(data['counterparty'], str),
                product=deserialize_optional(data['product'], EvmProduct.deserialize),
                address=deserialize_optional(data['address'], string_to_evm_address),
            )
        except KeyError as e:
            raise DeserializationError(f'Did not find key {e!s} in EvmSwapEvent data') from e

    def __repr__(self) -> str:
        fields = self._history_base_entry_repr_fields() + [
            f'{self.tx_hash=}',
            f'{self.counterparty=}',
            f'{self.product=}',
            f'{self.address=}',
        ]
        return f'EvmSwapEvent({", ".join(fields)})'

    def __str__(self) -> str:
        return (
            f'{self.event_subtype} EvmSwapEvent in {self.location} with '
            f'tx_hash={self.tx_hash.hex()} and time '
            f'{timestamp_to_date(ts_ms_to_sec(self.timestamp))} using {self.asset}'
        )

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.TRADE
