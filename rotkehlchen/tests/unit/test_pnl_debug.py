import json
from pathlib import Path

from rotkehlchen.accounting.importer.json import HistoryJSONImporter
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents


def test_pnl_debug_import(database):
    pnl_debug_file = Path(__file__).resolve().parent.parent / 'data' / 'pnl_debug.json'
    with open(pnl_debug_file) as f:
        pnl_debug_json = json.load(f)

    json_importer = HistoryJSONImporter(database)
    status, data = json_importer.import_history_debug(pnl_debug_file)
    assert status is True
    assert 'end_ts' in data['data']
    assert 'start_ts' in data['data']
    assert isinstance(data['data']['start_ts'], int)
    assert isinstance(data['data']['end_ts'], int)

    # compare data from json and db.
    events_from_file = pnl_debug_json['events']
    settings_from_file = pnl_debug_json['settings']
    settings_from_file.pop('last_write_ts')
    ignored_actions_ids_from_file = pnl_debug_json['ignored_events_ids']

    settings_from_db = database.get_settings().serialize()
    settings_from_db.pop('last_write_ts')
    ignored_actions_ids_from_db = database.get_ignored_action_ids(None)
    serialized_ignored_actions_from_db = {
        str(k): v for k, v in ignored_actions_ids_from_db.items()
    }
    dbevents = DBHistoryEvents(database)
    events_from_db = dbevents.get_history_events(HistoryEventFilterQuery.make(), False)
    serialized_events_from_db = [entry.serialize() for entry in events_from_db]

    assert settings_from_file == settings_from_db
    assert serialized_ignored_actions_from_db == ignored_actions_ids_from_file
    assert events_from_file == serialized_events_from_db
