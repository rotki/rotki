from typing import Any, Dict, List, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.db.utils import AssetBalance, LocationData, SingleAssetBalance
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_location_from_db
from rotkehlchen.typing import EthTokenInfo, Location, TradeType
from rotkehlchen.utils.version_check import VersionCheckResult


def _process_entry(entry: Any) -> Union[str, List[Any], Dict[str, Any], Any]:
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
            if isinstance(k, Asset):
                k = k.identifier
            new_dict[k] = _process_entry(v)
        return new_dict
    elif isinstance(entry, LocationData):
        return {
            'time': entry.time,
            'location': str(deserialize_location_from_db(entry.location)),
            'usd_value': entry.usd_value,
        }
    elif isinstance(entry, SingleAssetBalance):
        return {'time': entry.time, 'amount': entry.amount, 'usd_value': entry.usd_value}
    elif isinstance(entry, AssetBalance):
        return {
            'time': entry.time,
            'asset': entry.asset.identifier,
            'amount': entry.amount,
            'usd_value': entry.usd_value,
        }
    elif isinstance(entry, Trade):
        return entry.serialize()
    elif isinstance(entry, DBSettings):
        return entry._asdict()
    elif isinstance(entry, EthTokenInfo):
        return process_result(entry._asdict())
    elif isinstance(entry, VersionCheckResult):
        return process_result(entry._asdict())
    elif isinstance(entry, DBSettings):
        return process_result(entry._asdict())
    elif isinstance(entry, tuple):
        raise ValueError('Query results should not contain tuples')
    elif isinstance(entry, Asset):
        return entry.identifier
    elif isinstance(entry, (TradeType, Location)):
        return str(entry)
    else:
        return entry


def process_result(result: Dict[Any, Any]) -> Dict[Any, Any]:
    """Before sending out a result a dictionary via the server we are turning:

        - all Decimals to strings so that the serialization to float/big number
          is handled by the client application and we lose nothing in the transfer

        - if a dictionary has an Asset for a key use its identifier as the key value
        - all NamedTuples and Dataclasses must be serialized into dicts
    """
    processed_result = _process_entry(result)
    assert isinstance(processed_result, Dict)
    return processed_result


def process_result_list(result: List[Any]) -> List[Any]:
    """Just lke process_result but for lists"""
    processed_result = _process_entry(result)
    assert isinstance(processed_result, List)
    return processed_result
