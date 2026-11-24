from __future__ import annotations

import logging
import threading
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from flask import Response, after_this_request, jsonify, make_response, send_file

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Temp files that an export created for a later download, keyed by the path string the
# export returned to the client. The download endpoints take a client-supplied path, so
# they serve and delete only a file registered here, and only once. The client value is
# only a lookup key: the file that is served and deleted is the server's own Path.
_pending_downloads: Final[dict[str, Path]] = {}
_pending_downloads_lock = threading.Lock()


def register_pending_download(path: Path) -> None:
    """Allow a single download (and deletion) of a freshly exported temp file.

    The client must send back `str(path)`, which is what the export returns.
    """
    with _pending_downloads_lock:
        _pending_downloads[str(path)] = path


def _claim_pending_download(file_path: str) -> Path | None:
    """Remove and return the registered export for `file_path`, if there is one."""
    with _pending_downloads_lock:
        return _pending_downloads.pop(file_path, None)


def _remove_temp_export(temp_file: Path) -> None:
    try:
        temp_file.unlink()
        temp_file.parent.rmdir()
    except (FileNotFoundError, PermissionError, OSError) as e:
        log.warning('Failed to clean up after download of %s: %s', temp_file, e)


def discard_pending_downloads() -> None:
    """Delete the exports that were never downloaded, so they don't outlive the session."""
    with _pending_downloads_lock:
        pending = list(_pending_downloads.values())
        _pending_downloads.clear()
    for temp_file in pending:
        _remove_temp_export(temp_file)


def register_post_download_cleanup(temp_file: Path) -> None:
    @after_this_request
    def do_cleanup(response: Response) -> Response:
        _remove_temp_export(temp_file)
        return response


def make_download_response(file_path: str, mimetype: str) -> Response:
    """Serve a freshly exported file and delete it after the response is sent.

    Only a path that the export step registered with `register_pending_download`
    is served, and only once. Any other path is rejected as invalid input and
    left untouched.
    """
    if (path := _claim_pending_download(file_path)) is None:
        return make_response(
            (
                jsonify({'result': None, 'message': f'Invalid file path: {file_path}'}),
                HTTPStatus.BAD_REQUEST,
            ),
        )

    register_post_download_cleanup(path)
    return send_file(
        path_or_file=path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=path.name,
    )
