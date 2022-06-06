import json
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from marshmallow import EXCLUDE, ValidationError
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.v1.schemas import (
    HistoryBaseEntrySchema,
    IgnoredActionsModifySchema,
    ModifiableSettingsSchema,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import InputError
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HistoryJSONImporter:
    def __init__(self, db: DBHandler) -> None:
        self.db = db

    def import_history_debug(self, filepath: Path) -> Tuple[bool, Dict[str, Any]]:
        """Imports the user events, settings & ignored actions identifiers for debugging."""
        try:
            with open(filepath) as f:
                debug_data = json.load(f)
        except (PermissionError, json.JSONDecodeError) as e:
            error_msg = f'Failed to import history events due to: {str(e)}'
            return False, {'data': {}, 'msg': error_msg}

        has_required_keys = (
            'events' in debug_data and
            'settings' in debug_data and
            'ignored_events_ids' in debug_data
        )
        if has_required_keys is False:
            return False, {'data': {}, 'msg': 'import history data does not contain required keys'}
        has_required_types = (
            isinstance(debug_data['events'], list) and
            isinstance(debug_data['settings'], dict) and
            isinstance(debug_data['ignored_events_ids'], dict)
        )
        if has_required_types is False:
            return False, {
                'data': {},
                'msg': 'import history data contains some invalid data types',
            }

        # add history events.
        log.debug('Trying to add history events')
        history_db = DBHistoryEvents(self.db)
        try:
            for event in debug_data['events']:
                event = HistoryBaseEntrySchema(identifier_required=False).load(event)
                history_db.add_history_event(event['event'])
        except ValidationError as e:
            error_msg = f'Error while adding history events due to: {str(e)}'
            log.error(error_msg)
            return False, {'data': {}, 'msg': error_msg}
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            history_db.db.conn.rollback()
            error_msg = f'Error while adding history events due to: {str(e)}'
            log.error(error_msg)
            return False, {'data': {}, 'msg': error_msg}
        log.debug('Successfully added history events')

        # add settings
        log.debug('Trying to add settings')
        try:
            settings = ModifiableSettingsSchema().load(debug_data['settings'], unknown=EXCLUDE)
        except ValidationError as e:
            error_msg = f'Error while adding settings due to: {str(e)}'
            log.error(error_msg)
            return False, {'data': {}, 'msg': error_msg}
        self.db.set_settings(settings)
        log.debug('Successfully added settings')

        # add ignored events ids
        log.debug('Trying to add ignored actions identifiers')
        for action_type, action_ids in debug_data['ignored_events_ids'].items():
            try:
                ignored_event_id = IgnoredActionsModifySchema().load(
                    {'action_type': action_type, 'action_ids': action_ids},
                )
                self.db.add_to_ignored_action_ids(
                    action_type=ignored_event_id['action_type'],
                    identifiers=ignored_event_id['action_ids'],
                )
            except ValidationError as e:
                error_msg = f'Error while adding ignored action identifiers due to: {str(e)}'
                log.error(error_msg)
                return False, {'data': {}, 'msg': error_msg}
            except InputError as e:
                error_msg = f'Error while adding ignored action identifiers due to: {str(e)}'
                log.error(error_msg)
                return False, {'data': {}, 'msg': error_msg}

        log.debug('Successfully added ignored actions identifiers')
        first_event = HistoryBaseEntrySchema(identifier_required=False).load(
            data=debug_data['events'][0],
        )['event']
        last_event = HistoryBaseEntrySchema(identifier_required=False).load(
            data=debug_data['events'][-1],
        )['event']
        return True, {
            'data': {
                'start_ts': first_event.get_timestamp(),
                'end_ts': last_event.get_timestamp(),
            },
            'msg': '',
        }
