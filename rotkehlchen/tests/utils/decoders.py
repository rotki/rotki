from unittest.mock import _patch, patch


def patch_decoder_reload_data() -> _patch:
    """Patch to avoid reloading on-chain data at each decoding"""
    return patch(
        target='rotkehlchen.chain.evm.node_inquirer.should_update_protocol_cache',
        new=lambda *args, **kwargs: False,
    )
