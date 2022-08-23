import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from rotkehlchen.types import ChecksumEvmAddress


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class CurvePool:
    """Represent a curve pool contract with the position token and the assets in the pool"""
    lp: ChecksumEvmAddress
    assets: List[ChecksumEvmAddress]
    pool_address: ChecksumEvmAddress


def get_curve_pools() -> Dict[ChecksumEvmAddress, CurvePool]:
    """Get pools in a CurvePool structure from information file"""
    pools = {}
    dir_path = Path(__file__).resolve().parent.parent.parent.parent
    with open(dir_path / 'data' / 'curve_pools.json', 'r') as f:
        data = json.loads(f.read())
        for lp, info in data.items():
            pools[lp] = CurvePool(
                lp=lp,
                assets=info['assets'],
                pool_address=info['pool'],
            )
    return pools
