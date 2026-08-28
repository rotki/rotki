from typing import TYPE_CHECKING, Any

from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from rotkehlchen.db.settings import ModifiableDBSettings
    from rotkehlchen.rotkehlchen import Rotkehlchen


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
            new_settings = process_result(self.rotkehlchen.get_settings(cursor))
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        return True, '', new_settings | cache

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
            settings = process_result(self.rotkehlchen.get_settings(cursor))
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        return settings | cache
