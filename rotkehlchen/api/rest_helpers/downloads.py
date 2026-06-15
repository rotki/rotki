from __future__ import annotations

import logging
import tempfile
from http import HTTPStatus
from pathlib import Path

from flask import Response, after_this_request, jsonify, make_response, send_file

from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
