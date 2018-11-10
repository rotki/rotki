from typing import Dict, Union

from rotkehlchen.fval import FVal
from rotkehlchen.typing import Asset

# Types used by dbhander and datahandler
BalancesData = Dict[Union[str, Asset], Dict[str, Union[FVal, Dict]]]
DBSettings = Dict[str, Union[int, bool, str, None]]
ExternalTrade = Dict[str, Union[str, int]]
