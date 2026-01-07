from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import Response, after_this_request

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from pathlib import Path

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
