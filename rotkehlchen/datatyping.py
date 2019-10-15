from typing import Dict, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal

# Types used by dbhandler and datahandler
BalancesData = Dict[Union[str, Asset], Dict[str, Union[FVal, Dict]]]
ExternalTrade = Dict[str, Union[str, int]]
