from enum import auto

from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin


class NftHandling(SerializableEnumNameMixin):
    """How an asset search treats NFTs.

    NFTs are searched by a query of their own, separate from the asset search, so all three states
    are a choice of which queries to run rather than a filter applied afterwards. That distinction
    matters for SHOW_ONLY: the two result sets are merged and truncated to `limit` together, so a
    caller cannot get "NFTs only" by filtering what comes back.
    """
    EXCLUDE = auto()
    INCLUDE = auto()
    SHOW_ONLY = auto()
