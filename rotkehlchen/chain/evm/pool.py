from typing import Final

MIN_POOL_SIZE: Final = 1


def compute_rpc_pool_size(active_nodes: int, max_pool_size: int) -> int:
    """Return a capped pool size based on half the active node count (rounded up)."""
    if active_nodes <= 0:
        return MIN_POOL_SIZE

    capped_max_pool_size = max(MIN_POOL_SIZE, max_pool_size)
    return min(max(MIN_POOL_SIZE, (active_nodes + 1) // 2), capped_max_pool_size)
