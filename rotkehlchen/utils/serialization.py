import json
from typing import Dict, List, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import TradeType


class RKLDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        kwargs['object_hook'] = self.object_hook
        json.JSONDecoder.__init__(self, *args, **kwargs)

    def object_hook(self, obj):  # pylint: disable=no-self-use
        return rkl_decode_value(obj)


class RKLEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, FVal):
            return str(obj)
        if isinstance(obj, TradeType):
            return str(obj)
        if isinstance(obj, float):
            raise ValueError("Trying to json encode a float.")
        if isinstance(obj, Asset):
            return obj.identifier

        return json.JSONEncoder.default(self, obj)

    def _encode(self, obj):
        if isinstance(obj, dict):
            def transform_asset(o):
                return self._encode(o.identifier if isinstance(o, Asset) else o)
            return {transform_asset(k): transform_asset(v) for k, v in obj.items()}
        else:
            return obj

    def encode(self, obj):
        return super().encode(self._encode(obj))


def rlk_jsonloads(data: str) -> Union[Dict, List]:
    return json.loads(data, cls=RKLDecoder)


def rlk_jsonloads_dict(data: str) -> Dict:
    value = rlk_jsonloads(data)
    assert isinstance(value, dict)
    return value


def rlk_jsonloads_list(data: str) -> List:
    value = rlk_jsonloads(data)
    assert isinstance(value, list)
    return value


def rlk_jsondumps(data: Union[Dict, List]) -> str:
    return json.dumps(data, cls=RKLEncoder)


def rkl_decode_value(
        val: Union[Dict, List, float, bytes, str],
) -> Union[Dict, FVal, List, bytes, str]:
    if isinstance(val, dict):
        new_val = dict()
        for k, v in val.items():
            value = rkl_decode_value(v)
            if k == 'symbol' and isinstance(value, FVal):
                # In coin paprika's symbols and all the token's symbols
                # there are some symbols like 1337 which are all numeric and
                # are interpreted as numeric. Adjust for it here.
                value = str(v)
            new_val[k] = value
        return new_val
    elif isinstance(val, list):
        return [rkl_decode_value(x) for x in val]
    elif isinstance(val, float):
        return FVal(val)
    elif isinstance(val, (bytes, str)):
        try:
            val = float(val)
            return FVal(val)
        except ValueError:
            pass

    assert not isinstance(val, float)
    return val


def pretty_json_dumps(data: Dict) -> str:
    return json.dumps(
        data,
        sort_keys=True,
        indent=4,
        separators=(',', ': '),
        cls=RKLEncoder,
    )
