from collections.abc import Callable
from enum import auto
from typing import Literal

from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin


class IgnoredAssetsHandling(SerializableEnumNameMixin):
    NONE = auto()
    EXCLUDE = auto()
    SHOW_ONLY = auto()

    def operator(self) -> Literal['IN', 'NOT IN']:
        """Caller should make sure this is narrowed between exclude and show only"""
        if self == IgnoredAssetsHandling.EXCLUDE:
            return 'NOT IN'
        return 'IN'

    def get_should_skip_handler(self) -> Callable[[str, set[str]], bool]:
        """Returns a function that can be used to check if an ignored asset should be skipped.
        The caller of this function knowingly load the entire ignored assets in memory and use
        this function to include/exclude the ignored assets. This is because the ignored assets are
        stored in a different database and we avoid attaching/detaching the DB here due to:
        #7533 and https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=69334133
        TODO: Improve this to avoid loading the entire ignored assets in memory"""
        if self == IgnoredAssetsHandling.EXCLUDE:
            return lambda asset, ignored_assets: asset in ignored_assets
        if self == IgnoredAssetsHandling.SHOW_ONLY:
            return lambda asset, ignored_assets: asset not in ignored_assets
        return lambda asset, ignored_assets: False
