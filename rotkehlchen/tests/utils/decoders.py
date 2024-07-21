from contextlib import ExitStack
from unittest.mock import patch

from rotkehlchen.chain.ethereum.modules.convex.constants import CPT_CONVEX
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME


def patch_decoder_reload_data(load_global_caches: list[str] | None = None) -> ExitStack:
    """Patch to avoid reloading on-chain data at each decoding"""
    with ExitStack() as stack:
        stack.enter_context(patch(  # patch to not refresh cache by not downloading new data
            target='rotkehlchen.chain.evm.node_inquirer.should_update_protocol_cache',
            new=lambda *args, **kwargs: False,
        ))

        # patch_general and patch_unique are booleans to indicate if we want to patch
        # globaldb_get_general_cache_values and/or unique globaldb_get_unique_cache_value
        for counterparties, path, patch_general, patch_unique in (  # patch to not load cache from DB by default  # noqa: E501
            ({CPT_CONVEX}, 'rotkehlchen.chain.ethereum.modules.convex.convex_cache', True, True),
            ({CPT_CURVE}, 'rotkehlchen.chain.evm.decoding.curve.curve_cache', True, True),
            ({CPT_GEARBOX}, 'rotkehlchen.chain.evm.decoding.gearbox.gearbox_cache', True, True),
            ({CPT_AERODROME, CPT_VELODROME}, 'rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache', True, False),  # noqa: E501
        ):
            if load_global_caches is not None and any(cache in counterparties for cache in load_global_caches):  # noqa: E501
                continue

            if patch_general:
                stack.enter_context(
                    patch(path + '.globaldb_get_general_cache_values', side_effect=lambda *args, **kwargs: []),  # noqa: E501
                )
            if patch_unique:
                stack.enter_context(
                    patch(path + '.globaldb_get_unique_cache_value', side_effect=lambda *args, **kwargs: None),  # noqa: E501
                )

        return stack.pop_all()
