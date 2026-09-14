import json
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from rotkehlchen.db.settings import DBSettings, ModifiableDBSettings
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def serialize_settings(settings: DBSettings) -> dict[str, Any]:
    """Serialize the settings for the API, without the frontend settings blob.

    The blob is served by GET /settings/frontend as real JSON. Carrying it here as well would put
    two representations of one value in one response, and the string form is the one that cannot be
    partially updated - which is the whole reason the /settings/frontend resource exists.
    """
    serialized = process_result(settings)
    serialized.pop('frontend_settings', None)
    return serialized


class SettingsService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def set_settings(
            self,
            settings: ModifiableDBSettings,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        success, message = self.rotkehlchen.set_settings(settings)
        if not success:
            return False, message, None

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            new_settings = serialize_settings(self.rotkehlchen.get_settings(cursor))
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        return True, '', new_settings | cache

    def get_frontend_settings(self) -> dict[str, Any]:
        """Read the frontend settings blob as JSON.

        Anything that is not a JSON object answers as an empty one: the column defaults to the
        empty string, and a blob that does not parse has no partial update that could repair it.
        That matches what the PATCH endpoint does with such a blob, and what the client falls
        back to.
        """
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            raw = self.rotkehlchen.get_settings(cursor).frontend_settings

        if raw == '':
            return {}

        try:
            settings = json.loads(raw)
        except json.JSONDecodeError as e:
            log.error('Stored frontend settings are not valid JSON: %s', e)
            return {}

        return settings if isinstance(settings, dict) else {}

    def patch_frontend_settings(
            self,
            patch: dict[str, Any],
            remove: list[str],
    ) -> None:
        """Merge a partial update into the frontend settings blob"""
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            self.rotkehlchen.data.db.patch_frontend_settings(
                write_cursor=write_cursor,
                patch=patch,
                remove=remove,
            )

    def get_settings(self) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = serialize_settings(self.rotkehlchen.get_settings(cursor))
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        return settings | cache
