import os
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import psutil
import pytest
from flask import Flask

from rotkehlchen.api.rest_helpers.downloads import make_download_response


def unlink_closed_file(path: Path) -> None:
    assert str(path.resolve()) not in {
        str(Path(entry.path).resolve()) for entry in psutil.Process().open_files()
    }
    os.unlink(path)  # noqa: PTH108  # Bypass the patched Path.unlink.


@pytest.mark.parametrize('consume', [False, True])
@pytest.mark.parametrize('method', ['GET', 'HEAD'])
def test_export_cleanup_after_stream_close(consume: bool, method: str) -> None:
    """WSGI cleanup releases the file before unlinking, including aborted and HEAD requests."""
    with TemporaryDirectory() as directory:
        export_dir = Path(directory) / 'export'
        export_dir.mkdir()
        filepath = export_dir / 'history.csv'
        contents = b'x' * (3 * 8192)
        filepath.write_bytes(contents)
        app = Flask(__name__)
        app.add_url_rule('/export', endpoint='export', view_func=partial(
            make_download_response, file_path=str(filepath), mimetype='text/csv',
        ))
        with patch.object(Path, 'unlink', autospec=True, side_effect=unlink_closed_file) as unlink:
            response = app.test_client().open('/export', method=method, buffered=False)
            try:
                unlink.assert_not_called()
                assert str(filepath.resolve()) in {
                    str(Path(entry.path).resolve()) for entry in psutil.Process().open_files()
                }
                if consume:
                    assert response.get_data() == (contents if method == 'GET' else b'')
            finally:
                response.close()
            unlink.assert_called_once_with(filepath)
            assert not export_dir.exists()
            assert str(filepath.resolve()) not in {
                str(Path(entry.path).resolve()) for entry in psutil.Process().open_files()
            }
