from __future__ import annotations

import logging
import tempfile
from contextlib import closing
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

from flask import Response, after_this_request, jsonify, make_response, send_file

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Iterator

    from werkzeug.wsgi import ClosingIterator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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


def register_post_download_cleanup(temp_file: Path) -> None:
    @after_this_request
    def do_cleanup(response: Response) -> Response:
        try:
            temp_file.unlink()
            temp_file.parent.rmdir()
        except (FileNotFoundError, PermissionError, OSError) as e:
            log.warning(f'Failed to clean up after download of {temp_file}: {e!s}')
        return response


def _is_within_temp_dir(path: Path) -> bool:
    """Check that `path` resolves to a location inside the system temp directory."""
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):  # RuntimeError: symlink loop while resolving
        return False
    return resolved.is_relative_to(Path(tempfile.gettempdir()).resolve())


def make_download_response(file_path: str, mimetype: str) -> Response:
    """Serve a freshly-exported file and delete it after the response is sent.

    Exports are always created under the system temp directory, so the requested
    path is validated to live within it before being served and cleaned up. Any
    other path is rejected as invalid input.
    """
    if not _is_within_temp_dir(path := Path(file_path)):
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
