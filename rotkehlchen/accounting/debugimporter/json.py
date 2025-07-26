import json
import logging
from pathlib import Path
from typing import Any

from marshmallow import EXCLUDE, ValidationError

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.api.v1.schemas import ModifiableSettingsSchema
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Loan, MarginPosition
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.swap import SwapEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DebugHistoryImporter:
    def __init__(self, db: DBHandler) -> None:
        self.db = db

    def import_history_debug(
            self,
            filepath: Path,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Imports the user events, settings & ignored actions identifiers for debugging."""
        try:
            with open(filepath, encoding='utf-8') as f:
                debug_data = json.load(f)
        except (PermissionError, json.JSONDecodeError) as e:
            error_msg = f'Failed to import history events due to: {e!s}'
            return False, error_msg, {}

        has_required_types = (
            isinstance(debug_data['events'], list) and
            isinstance(debug_data['settings'], dict) and
            isinstance(debug_data['ignored_events_ids'], list)
        )
        if has_required_types is False:
            error_msg = 'import history data contains some invalid data types'
            return False, error_msg, {}

        log.debug('Trying to add history events')
        events: list[AccountingEventMixin] = []
        try:
            for event in debug_data['events']:
                if 'extra_data' not in event:  # May be missing for non EVM events in old debug data  # noqa: E501
                    event['extra_data'] = None
                event_type = AccountingEventType.deserialize(event['accounting_event_type'])
                match event_type:
                    case AccountingEventType.TRADE:
                        events.append(SwapEvent.deserialize(event))
                    case AccountingEventType.ASSET_MOVEMENT:
                        events.append(AssetMovement.deserialize(event))
                    case AccountingEventType.MARGIN_POSITION:
                        events.append(MarginPosition.deserialize(event))
                    case AccountingEventType.LOAN:
                        events.append(Loan.deserialize(event))
                    case AccountingEventType.HISTORY_EVENT:
                        events.append(HistoryEvent.deserialize(event))
                    case AccountingEventType.TRANSACTION_EVENT:
                        events.append(EvmEvent.deserialize(event))
                    case AccountingEventType.FEE | AccountingEventType.PREFORK_ACQUISITION:
                        log.info(f'Skipping {event_type} from imported json report: {event}')
        except (DeserializationError, KeyError, UnknownAsset) as e:
            error_msg = f'Error while adding events due to: {e!s}'
            log.exception(error_msg)
            return False, error_msg, {}

        log.debug('Trying to add settings')
        try:
            settings = ModifiableSettingsSchema().load(debug_data['settings'], unknown=EXCLUDE)
        except (ValidationError, KeyError) as e:
            error_msg = f'Error while adding settings due to: {e!s}'
            log.error(error_msg)
            return False, error_msg, {}
        with self.db.user_write() as cursor:
            self.db.set_settings(write_cursor=cursor, settings=settings)

        log.debug('Trying to add ignored actions identifiers')
        try:
            if not isinstance((action_ids := debug_data['ignored_events_ids']), list) and all(isinstance(x, str) for x in action_ids):  # noqa: E501
                raise DeserializationError('Ignored event ids are not a list of strings')
            with self.db.user_write() as cursor:
                self.db.add_to_ignored_action_ids(
                    write_cursor=cursor,
                    identifiers=debug_data['ignored_events_ids'],
                )
        except (DeserializationError, InputError, KeyError) as e:
            err_str = f'missing key: {e}' if isinstance(e, KeyError) else str(e)
            error_msg = f'Error while adding ignored action identifiers due to {err_str}'
            log.error(error_msg)
            return False, error_msg, {}

        log.debug('Trying to validate pnl settings')
        try:
            from_ts = debug_data['pnl_settings']['from_timestamp']
            to_ts = debug_data['pnl_settings']['to_timestamp']
            if isinstance(from_ts, int) is not True or isinstance(to_ts, int) is not True:
                error_msg = 'Expected integers as type for `from_timestamp` & `to_timestamp`'
                return False, error_msg, {}
        except KeyError as e:
            error_msg = f'Error while validating pnl settings due to: {e!s}'
            return False, error_msg, {}

        return True, '', {'events': events, 'pnl_settings': debug_data['pnl_settings']}
