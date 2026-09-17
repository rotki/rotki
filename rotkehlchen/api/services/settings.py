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
    """Serialize the settings for the API, without the blob GET /settings/frontend serves"""
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
        """Read the frontend settings blob, or an empty object if it is not a JSON object"""
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
