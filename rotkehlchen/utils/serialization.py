import json
from typing import Any, Dict, List, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Location, TradeType

DecodableValue = Union[Dict, List, float, bytes, str, int, FVal]
DecodedValue = Union[Dict, FVal, List, bytes, str, int]


class RKLEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, FVal):
            return str(obj)
        if isinstance(obj, (TradeType, Location)):
            return str(obj)
        if isinstance(obj, float):
            raise ValueError("Trying to json encode a float.")
        if isinstance(obj, Asset):
            return obj.identifier

        return json.JSONEncoder.default(self, obj)

    def _encode(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            def transform_asset(o: Any) -> Any:
                return self._encode(o.identifier if isinstance(o, Asset) else o)
            return {transform_asset(k): transform_asset(v) for k, v in obj.items()}
        # else
        return obj

    def encode(self, obj: Any) -> Any:
        return super().encode(self._encode(obj))


def jsonloads_dict(data: str) -> Dict[str, Any]:
    value = json.loads(data)
    assert isinstance(value, dict)
    return value


def jsonloads_list(data: str) -> List:
    value = json.loads(data)
    assert isinstance(value, list)
    return value


def rlk_jsondumps(data: Union[Dict, List]) -> str:
    return json.dumps(data, cls=RKLEncoder)


def pretty_json_dumps(data: Dict) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        indent=4,
        separators=(',', ': '),
        cls=RKLEncoder,
    )
