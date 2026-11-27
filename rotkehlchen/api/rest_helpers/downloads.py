from __future__ import annotations

import logging
import threading
from contextlib import closing
from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, cast

from flask import Response, send_file
from werkzeug.wsgi import ClosingIterator

from rotkehlchen.api.result import FailResult, api_response
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Temp files that an export created for a later download, keyed by the path string the
# export returned to the client. The download endpoints take a client-supplied path, so
# they serve and delete only a file registered here, and only once. The client value is
# only a lookup key: the file that is served and deleted is the server's own Path.
_pending_downloads: Final[dict[str, Path]] = {}
_pending_downloads_lock = threading.Lock()
# Bumped each time a user session ends. An export captures it before it starts working,
# so an api task abandoned at logout or shutdown that finishes later cannot register its
# file into a session that was already cleaned up (or into the next user's session).
_download_session = 0


def current_download_session() -> int:
    """Return the token an export passes to `register_pending_download`.

    Call it when the export starts, not when it finishes.
    """
    with _pending_downloads_lock:
        return _download_session


def register_pending_download(path: Path, session: int) -> None:
    """Allow a single download (and deletion) of a freshly exported temp file.

    The client must send back `str(path)`, which is what the export returns.
    If the session the export started in has ended, the file is deleted instead.
    """
    with _pending_downloads_lock:
        if session == _download_session:
            _pending_downloads[str(path)] = path
            return

    log.debug('Discarding an export that finished after its session ended')
    _remove_temp_export(path)


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
    """End the download session: delete the exports that were never downloaded,
    so they don't outlive the session, and refuse later registrations from it."""
    global _download_session  # noqa: PLW0603  # module level registry state
    with _pending_downloads_lock:
        _download_session += 1
        pending = list(_pending_downloads.values())
        _pending_downloads.clear()
    for temp_file in pending:
        _remove_temp_export(temp_file)


def close_before_last_chunk(stream: ClosingIterator) -> Iterator[bytes]:
    """Close a download before yielding the bytes that satisfy the client's Content-Length.

    Keep one chunk pending so full and range downloads release their file before the
    client can consider the transfer complete and request deletion of that file.
    """
    with closing(stream):
        chunk = next(stream, b'')
        for next_chunk in stream:
            yield chunk
            chunk = next_chunk
    if chunk:
        yield chunk


def close_stream_before_last_chunk(response: Response) -> Response:
    """Release a send_file response's handle before delivery of its final chunk.

    The outer close callback also releases the handle when streaming never starts.
    Normalizing the iterable keeps this safe for responses without a close method.
    """
    stream = ClosingIterator(cast('Iterable[bytes]', response.response))
    response.response = ClosingIterator(close_before_last_chunk(stream), stream.close)
    return response


def register_post_download_cleanup(response: Response, temp_file: Path) -> Response:
    """Delete an export after its stream closes, including on early disconnect."""
    response.direct_passthrough = False
    response.call_on_close(partial(_remove_temp_export, temp_file))
    return response


def make_download_response(file_path: str, mimetype: str) -> Response:
    """Serve a freshly exported file and delete it after the response is sent.

    Only a path that the export step registered with `register_pending_download`
    is served, and only once. Any other path is rejected as invalid input and
    left untouched.
    """
    if (path := _claim_pending_download(file_path)) is None:
        return api_response(FailResult(
            f'Invalid file path: {file_path}',
            HTTPStatus.BAD_REQUEST,
            FailureCause.INVALID_INPUT,
        ))

    response = send_file(
        path_or_file=path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=path.name,
    )
    return register_post_download_cleanup(response, path)
