from __future__ import annotations

from contextlib import suppress
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.rest_helpers.history_events import edit_grouped_events_with_optional_fee
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.filtering import DBEqualsFilter, DBMultiIntegerFilter, DBTimestampFilter
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import AlreadyExists, InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.filtering import HistoryBaseEntryFilterQuery
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.rotkehlchen import Rotkehlchen


class HistoryEventsService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def add_history_events(self, events: list[HistoryBaseEntry]) -> dict[str, Any]:
        if (error := self._ensure_event_tx_existence(events[0])) is not None:
            return error

        db = DBHistoryEvents(self.rotkehlchen.data.db)
        main_identifier = None
        try:
            with self.rotkehlchen.data.db.user_write() as cursor:
                for idx, event in enumerate(events):
                    identifier = db.add_history_event(
                        write_cursor=cursor,
                        event=event,
                        mapping_values={
                            HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED,
                        },
                    )
                    if idx == 0:
                        main_identifier = identifier
        except (sqlcipher.DatabaseError, OverflowError) as e:  # pylint: disable=no-member
            error_msg = f'Failed to add event to the DB due to a DB error: {e!s}'
            return {
                'result': None,
                'message': error_msg,
                'status_code': HTTPStatus.CONFLICT,
            }

        if main_identifier is None:
            error_msg = 'Failed to add event to the DB. It already exists'
            return {
                'result': None,
                'message': error_msg,
                'status_code': HTTPStatus.CONFLICT,
            }

        return {
            'result': {'identifier': main_identifier},
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def edit_history_events(
            self,
            events: list[HistoryBaseEntry],
            identifiers: list[int] | None,
    ) -> dict[str, Any]:
        if (error := self._ensure_event_tx_existence(events[0])) is not None:
            return error

        events_db = DBHistoryEvents(self.rotkehlchen.data.db)
        if (events_type := events[0].entry_type) in {
            HistoryBaseEntryType.ASSET_MOVEMENT_EVENT,
            HistoryBaseEntryType.SWAP_EVENT,
            HistoryBaseEntryType.EVM_SWAP_EVENT,
            HistoryBaseEntryType.SOLANA_SWAP_EVENT,
        }:
            try:
                with events_db.db.conn.write_ctx() as write_cursor:
                    edit_grouped_events_with_optional_fee(
                        events_db=events_db,
                        write_cursor=write_cursor,
                        events=events,
                        events_type=events_type,
                        identifiers=identifiers,
                    )
            except InputError as e:
                return {
                    'result': None,
                    'message': str(e),
                    'status_code': HTTPStatus.CONFLICT,
                }
            else:
                return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

        try:
            with self.rotkehlchen.data.db.user_write() as write_cursor:
                for event in events:
                    events_db.edit_history_event(
                        event=event,
                        write_cursor=write_cursor,
                    )
        except InputError as e:
            return {
                'result': None,
                'message': str(e),
                'status_code': HTTPStatus.CONFLICT,
            }

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_history_events(
            self,
            filter_query: HistoryBaseEntryFilterQuery,
            force_delete: bool,
    ) -> dict[str, Any]:
        db = DBHistoryEvents(self.rotkehlchen.data.db)
        ids_to_delete = db.get_history_events_identifiers(filter_query=filter_query)

        # Check if identifiers were explicitly requested and verify all exist
        # Only do this check when identifiers is the only meaningful filter (excluding timestamp
        # filter which always exists). This preserves backward compatibility while allowing
        # combined filters to work as an intersection.
        requested_ids: list[int] | None = None
        has_other_filters = False
        for fil in filter_query.filters:
            if isinstance(fil, DBMultiIntegerFilter) and fil.column == 'history_events_identifier':
                requested_ids = list(fil.values)
            elif not isinstance(fil, (DBTimestampFilter, DBEqualsFilter)):
                # DBTimestampFilter always exists, DBEqualsFilter for ignored=0 is just a default
                has_other_filters = True

        if requested_ids is not None and not has_other_filters:
            # Verify all requested IDs were found (check in order to report first missing)
            found_ids = set(ids_to_delete)
            for requested_id in requested_ids:
                if requested_id not in found_ids:
                    return {
                        'result': None,
                        'message': f'Tried to remove history event with id {requested_id} which does not exist',  # noqa: E501
                        'status_code': HTTPStatus.CONFLICT,
                    }

        if len(ids_to_delete) == 0:
            return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

        error_msg = db.delete_history_events_by_identifier(
            identifiers=ids_to_delete,
            force_delete=force_delete,
        )
        if error_msg is not None:
            return {
                'result': None,
                'message': error_msg,
                'status_code': HTTPStatus.CONFLICT,
            }

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def _ensure_event_tx_existence(self, event: HistoryBaseEntry) -> dict[str, Any] | None:
        """Check if an evm/evmlike event tx is present in the DB and if not, query it from onchain.
        Returns None if the tx was successfully found, or if the event is not an evm event,
        otherwise returns error data for the response.
        """
        if not isinstance(event, EvmEvent):
            return None

        blockchain = SupportedBlockchain.from_location(event.location)  # type: ignore[arg-type]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            table = 'zksynclite_transactions' if blockchain.is_evmlike() else 'evm_transactions'
            if cursor.execute(
                f'SELECT COUNT(*) FROM {table} WHERE tx_hash=?',
                (event.tx_ref,),
            ).fetchone()[0] != 0:
                return None

        try:
            associated_address = deserialize_evm_address(event.location_label)  # type: ignore  # if label is None TypeError will be caught
        except (DeserializationError, TypeError):
            return {
                'result': None,
                'message': 'The location_label must be set to a valid EVM address to pull the tx for the given hash from onchain.',  # noqa: E501
                'status_code': HTTPStatus.BAD_REQUEST,
            }

        if blockchain.is_evmlike():
            if self.rotkehlchen.chains_aggregator.zksync_lite.query_single_transaction(
                tx_hash=event.tx_ref,
                concerning_address=associated_address,
            ) is not None:
                return None
        else:
            with suppress(KeyError, DeserializationError, RemoteError, AlreadyExists, InputError):
                self.rotkehlchen.chains_aggregator.get_chain_manager(  # type: ignore[call-overload]
                    blockchain=blockchain,
                ).transactions.add_transaction_by_hash(
                    tx_hash=event.tx_ref,
                    associated_address=associated_address,
                )
                return None

        return {
            'result': None,
            'message': f'The provided transaction hash does not exist for {event.location.name.lower()}.',  # noqa: E501
            'status_code': HTTPStatus.BAD_REQUEST,
        }
