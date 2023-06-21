from typing import TYPE_CHECKING
from unittest.mock import _patch, patch

from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def patch_decoder_reload_data() -> _patch:
    """Patch decoder so reload data does not reload on-chain data at each decoding"""
    def patched_reload_data(self, cursor: 'DBCursor') -> None:
        self.base.refresh_tracked_accounts(cursor)
        for decoder in self.decoders.values():
            if isinstance(decoder, CustomizableDateMixin):
                decoder.reload_settings(cursor)

    return patch('rotkehlchen.chain.evm.decoding.decoder.EVMTransactionDecoder.reload_data', patched_reload_data)  # noqa: E501
