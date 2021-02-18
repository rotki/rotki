import json
from typing import Any, Dict, List, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Location, TradeType

DecodableValue = Union[Dict, List, float, bytes, str, int, FVal]
DecodedValue = Union[Dict, FVal, List, bytes, str, int]


class RKLDecoder(json.JSONDecoder):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs['object_hook'] = self.object_hook
        json.JSONDecoder.__init__(self, *args, **kwargs)

    def object_hook(self, obj: DecodableValue) -> DecodedValue:  # pylint: disable=no-self-use,method-hidden  # noqa: E501
        return rkl_decode_value(obj)


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


def rlk_jsonloads(data: str) -> Union[Dict, List]:
    return json.loads(data, cls=RKLDecoder)


def rlk_jsonloads_dict(data: str) -> Dict[str, Any]:
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
        val: DecodableValue,
) -> DecodedValue:
    """Decodes a value seen externally, most likely an API call

    This is mostly used to make sure that all string floats end up as FVal when
    coming into the app. There is one problem with this as can be seen below.
    There are some exceptions where strings get mistakenly turned into FVals.

    TODO: With all the other deserialization functions think if this is still needed
    or if it can go away and most of its functionality integrated there.
    """
    if isinstance(val, dict):
        new_val = {}
        for k, v in val.items():
            value = rkl_decode_value(v)
            # In some places such as coin paprika's symbols
            # binance pairs e.t.c.
            # there are some symbols like 1337 which are all numeric and
            # are interpreted as FVAL. Adjust for it here.
            should_not_be_fval = (
                (k == 'name' and isinstance(value, (FVal, int))) or
                (k == 'symbol' and isinstance(value, (FVal, int))) or
                (k == 'baseAsset' and isinstance(value, (FVal, int))) or
                (k == 'tradeId' and isinstance(value, (FVal, int))) or
                (k == 'id' and isinstance(value, (FVal, int))) or
                (k == 'quoteAsset' and isinstance(value, (FVal, int)))
            )
            if should_not_be_fval:
                value = str(v)
            new_val[k] = value
        return new_val
    if isinstance(val, list):
        return [rkl_decode_value(x) for x in val]
    if isinstance(val, float):
        return FVal(val)
    if isinstance(val, (bytes, str)):
        try:  # try to interpet it as an integer
            val = int(val)
            return val
        except ValueError:
            try:  # if not then try to interpet as an Fval
                val = FVal(val)
                return val
            except ValueError:
                pass  # then just return it as string

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
