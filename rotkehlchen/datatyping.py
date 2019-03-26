from typing import Dict, Union

from rotkehlchen.assets import Asset
from rotkehlchen.fval import FVal

# Types used by dbhander and datahandler
BalancesData = Dict[Union[str, Asset], Dict[str, Union[FVal, Dict]]]
DBSettings = Dict[str, Union[int, bool, str, None]]
ExternalTrade = Dict[str, Union[str, int]]
