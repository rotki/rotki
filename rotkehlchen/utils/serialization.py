import json
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Union

from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    FiatAsset,
    UnderlyingToken,
)
from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, EvmTokenKind, Location, Timestamp, TradeType


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


def deserialize_asset_with_oracles_from_db(
        asset_type: AssetType,
        asset_data: List[Any],
        underlying_tokens: Optional[List[UnderlyingToken]],
        form_with_incomplete_data: bool,
) -> AssetWithOracles:
    """
    From a db tuple containing information about any asset deserialize to the correct Asset class
    according to type in the database.
    May raise:
    - DeserializationError
    - UnknownAsset
    - WrongAssetType
    """
    identifier = asset_data[0]
    if asset_type == AssetType.EVM_TOKEN:
        decimals = asset_data[3]
        if decimals is None:
            decimals = 18
        name = asset_data[4]
        symbol = asset_data[5]
        missing_basic_data = name is None or symbol is None
        if missing_basic_data and form_with_incomplete_data is False:
            raise UnknownAsset(identifier=identifier)

        return EvmToken.initialize(
            address=asset_data[2],
            chain=ChainID(asset_data[12]),
            token_kind=EvmTokenKind.deserialize_from_db(asset_data[13]),
            decimals=decimals,
            name=name,
            symbol=symbol,
            started=Timestamp(asset_data[6]),
            swapped_for=CryptoAsset(asset_data[8]) if asset_data[8] is not None else None,
            coingecko=asset_data[9],
            cryptocompare=asset_data[10],
            protocol=asset_data[11],
            underlying_tokens=underlying_tokens,
        )
    if asset_type == AssetType.FIAT:
        return FiatAsset.initialize(
            identifier=identifier,
            name=asset_data[4],
            symbol=asset_data[5],
            coingecko=asset_data[9],
            cryptocompare=asset_data[10],
        )

    return CryptoAsset.initialize(
        identifier=asset_data[0],
        asset_type=asset_type,
        name=asset_data[4],
        symbol=asset_data[5],
        started=asset_data[6],
        forked=asset_data[7],
        swapped_for=asset_data[8],
        coingecko=asset_data[9],
        cryptocompare=asset_data[10],
    )


def deserialize_generic_asset_from_db(
        asset_type: AssetType,
        asset_data: List[Any],
        underlying_tokens: Optional[List[UnderlyingToken]],
        form_with_incomplete_data: bool,
) -> AssetWithNameAndType:
    """
    From a db tuple containing information about any asset deserialize to the correct Asset class
    according to type in the database. Is a wrapper around deserialize_asset_with_oracles_from_db
    And extends it by allowing the deserialization of CustomAsset objets.
    May raise:
    - DeserializationError
    - UnknownAsset
    - WrongAssetType
    """
    identifier = asset_data[0]
    if asset_type == AssetType.CUSTOM_ASSET:
        return CustomAsset.initialize(
            identifier=identifier,
            name=asset_data[4],
            custom_asset_type=asset_data[15],
            notes=asset_data[14],
        )

    return deserialize_asset_with_oracles_from_db(
        asset_type=asset_type,
        asset_data=asset_data,
        underlying_tokens=underlying_tokens,
        form_with_incomplete_data=form_with_incomplete_data,
    )
