from typing import Any, Dict, List, Union

from rotkehlchen.db.dbhandler import LocationData, SingleAssetBalance
from rotkehlchen.fval import FVal


def _process_entry(entry: Any) -> Union[str, List, Dict]:
    if isinstance(entry, FVal):
        return str(entry)
    elif isinstance(entry, list):
        new_list = list()
        for new_entry in entry:
            new_list.append(_process_entry(new_entry))
        return new_list
    elif isinstance(entry, dict):
        new_dict = dict()
        for k, v in entry.items():
            new_dict[k] = _process_entry(v)
        return new_dict
    elif isinstance(entry, LocationData):
        return {'time': entry.time, 'location': entry.location, 'usd_value': entry.usd_value}
    elif isinstance(entry, SingleAssetBalance):
        return {'time': entry.time, 'amount': entry.amount, 'usd_value': entry.usd_value}
    elif isinstance(entry, tuple):
        raise ValueError('Query results should not contain tuples')
    else:
        return entry


def process_result(result: Dict) -> Dict:
    """Before sending out a result a dictionary via the server we are turning
    all Decimals to strings so that the serialization to float/big number is handled
    by the client application and we lose nothing in the transfer"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, Dict)
    return processed_result


def process_result_list(result: List) -> List:
    """Just lke process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, List)
    return processed_result
