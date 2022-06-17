from pathlib import Path

from rotkehlchen.accounting.debugimporter.json import DebugHistoryImporter
from rotkehlchen.tests.utils.history import assert_pnl_debug_import


def test_pnl_debug_import(database):
    pnl_debug_file = Path(__file__).resolve().parent.parent / 'data' / 'pnl_debug.json'

    json_importer = DebugHistoryImporter(database)
    status, data = json_importer.import_history_debug(pnl_debug_file)
    assert status is True
    assert 'end_ts' in data['data']
    assert 'start_ts' in data['data']
    assert isinstance(data['data']['start_ts'], int)
    assert isinstance(data['data']['end_ts'], int)

    # compare data from json and db.
    assert_pnl_debug_import(filepath=pnl_debug_file, database=database)
