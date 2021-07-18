import json
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Location, TradeType


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
    """Just like jsonloads but forces the result to be a Dict"""
    value = json.loads(data)
    if not isinstance(value, dict):
        raise JSONDecodeError(msg='Returned json is not a dict', doc='{}', pos=0)
    return value


def jsonloads_list(data: str) -> List:
    """Just like jsonloads but forces the result to be a List"""
    value = json.loads(data)
    if not isinstance(value, list):
        raise JSONDecodeError(msg='Returned json is not a list', doc='{}', pos=0)
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
