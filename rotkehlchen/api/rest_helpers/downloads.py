from __future__ import annotations

import logging
import threading
from http import HTTPStatus
from pathlib import Path
from typing import Final

from flask import Response, after_this_request, jsonify, make_response, send_file

from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Temp files that an export created for a later download. The download endpoints take
# a client-supplied path, so they serve and delete only a path registered here, and
# only once. Anything else, including other files under the temp directory, is refused.
_pending_downloads: Final[set[Path]] = set()
_pending_downloads_lock = threading.Lock()


def _resolve(path: Path) -> Path | None:
    try:
        return path.resolve()
    except (OSError, RuntimeError):  # RuntimeError: symlink loop while resolving
        return None


def register_pending_download(path: Path) -> None:
    """Allow a single download (and deletion) of a freshly exported temp file."""
    if (resolved := _resolve(path)) is None:
        return
    with _pending_downloads_lock:
        _pending_downloads.add(resolved)


def _claim_pending_download(path: Path) -> bool:
    """Remove `path` from the pending downloads and return whether it was there."""
    if (resolved := _resolve(path)) is None:
        return False
    with _pending_downloads_lock:
        if resolved not in _pending_downloads:
            return False
        _pending_downloads.remove(resolved)
        return True


def _remove_temp_export(temp_file: Path) -> None:
    try:
        temp_file.unlink()
        temp_file.parent.rmdir()
    except (FileNotFoundError, PermissionError, OSError) as e:
        log.warning('Failed to clean up after download of %s: %s', temp_file, e)


def discard_pending_downloads() -> None:
    """Delete the exports that were never downloaded, so they don't outlive the session."""
    with _pending_downloads_lock:
        pending = list(_pending_downloads)
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
    if not _claim_pending_download(path := Path(file_path)):
        return make_response(
            (
                jsonify({'result': None, 'message': f'Invalid file path: {file_path}'}),
                HTTPStatus.BAD_REQUEST,
            ),
        )

    register_post_download_cleanup(path)
    return send_file(
        path_or_file=file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=path.name,
    )
