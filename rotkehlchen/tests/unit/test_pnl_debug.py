from pathlib import Path

from rotkehlchen.accounting.debugimporter.json import DebugHistoryImporter
from rotkehlchen.tests.utils.history import assert_pnl_debug_import


def test_pnl_debug_import(database):
    pnl_debug_file = Path(__file__).resolve().parent.parent / 'data' / 'pnl_debug.json'

    json_importer = DebugHistoryImporter(database)
    status, msg, data = json_importer.import_history_debug(pnl_debug_file)
    assert status is True
    assert msg == ''
    assert len(data['events']) == 17
    assert 'from_timestamp' in data['pnl_settings']
    assert 'to_timestamp' in data['pnl_settings']

    assert isinstance(data['pnl_settings']['from_timestamp'], int) is True
    assert isinstance(data['pnl_settings']['to_timestamp'], int) is True

    # compare data from json and db.
    assert_pnl_debug_import(filepath=pnl_debug_file, database=database)
