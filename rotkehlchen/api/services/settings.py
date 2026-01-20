from typing import Any

from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.serialize import process_result


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

    def get_settings(self) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = process_result(self.rotkehlchen.get_settings(cursor))
            cache = self.rotkehlchen.data.db.get_cache_for_api(cursor)
        return settings | cache
