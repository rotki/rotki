import csv
import json
import logging
from collections import defaultdict
from collections.abc import Iterator, Sequence
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, Final, NamedTuple

import requests

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, FValWithTolerance, Timestamp
from rotkehlchen.utils.misc import is_production, ts_now
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SMALLEST_AIRDROP_SIZE: Final = 20900
AIRDROPS_REPO_BASE: Final = f'https://raw.githubusercontent.com/rotki/data/{"main" if is_production() else "develop"}'  # noqa: E501
AIRDROPS_INDEX: Final = f'{AIRDROPS_REPO_BASE}/airdrops/index_v1.json'


class Airdrop(NamedTuple):
    """Airdrop class for representing airdrop data.

    This contains the definition of the Airdrop class, which is used to represent
    individual airdrops along with their associated data, such as URL, token address,
    website URL, name, and icon filename.
    """
    csv_path: str
    asset: CryptoAsset
    url: str
    name: str
    icon: str
    cutoff_time: Timestamp | None = None


class AirdropClaimEventQueryParams(NamedTuple):
    """Params used in the SQL query to detect as claimed an airdrop"""
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType
    location_label: ChecksumEvmAddress
    asset: CryptoAsset
    tolerance: FValWithTolerance


def _parse_airdrops(database: 'DBHandler', airdrops_data: dict[str, Any]) -> dict[str, Airdrop]:
    """Parses the airdrops' data from airdrops metadata index. Also, creates the new token if
    it's not present in the DB.

    May raise - RemoteError if the metadata is invalid.
    """
    airdrops: dict[str, Airdrop] = {}
    for protocol_name, airdrop_data in airdrops_data.items():
        try:
            if (new_asset_data := airdrop_data.get('new_asset_data')) is not None:
                try:
                    if (chain_id_raw := new_asset_data.get('chain_id')) is not None:
                        chain_id = ChainID.deserialize(chain_id_raw)
                    new_asset_type = AssetType.deserialize(new_asset_data['asset_type'])
                except DeserializationError as e:
                    log.error(f'Airdrops Index contains an invalid ChainID or AssetType of a token for {protocol_name}. {e!s}')  # noqa: E501
                    continue

                if new_asset_type == AssetType.EVM_TOKEN:
                    crypto_asset: CryptoAsset = get_or_create_evm_token(
                        userdb=database,
                        evm_address=new_asset_data['address'],
                        chain_id=chain_id,
                        decimals=new_asset_data['decimals'],
                        name=new_asset_data['name'],
                        symbol=new_asset_data['symbol'],
                    )
                elif (asset := Asset(airdrop_data['asset_identifier'])).exists() is True:
                    crypto_asset = asset.resolve_to_crypto_asset()  # use the local values of user, if it pre-existed  # noqa: E501
                else:
                    crypto_asset = CryptoAsset.initialize(
                        identifier=airdrop_data['asset_identifier'],
                        asset_type=new_asset_type,
                        name=new_asset_data['name'],
                        symbol=new_asset_data['symbol'],
                        coingecko=new_asset_data.get('coingecko'),
                        cryptocompare=new_asset_data.get('cryptocompare'),
                    )
                    GlobalDBHandler.add_asset(crypto_asset)
            else:
                try:
                    crypto_asset = Asset(airdrop_data['asset_identifier']).resolve_to_crypto_asset()  # noqa: E501
                except UnknownAsset as e:
                    log.error(f"Airdrops Index did not provide any data for {airdrop_data['asset_identifier']}. {e!s}")  # noqa: E501
                    continue

            airdrops[protocol_name] = Airdrop(
                asset=crypto_asset,
                csv_path=f"{AIRDROPS_REPO_BASE}/{airdrop_data['csv_path']}",
                url=airdrop_data['url'],
                name=airdrop_data['name'],
                icon=airdrop_data['icon'],
                cutoff_time=airdrop_data.get('cutoff_time'),
            )
        except KeyError as e:
            log.error(f'Airdrops Index does not contain a valid key for {protocol_name}. {e!s}')
    return airdrops


def fetch_airdrops_metadata(database: 'DBHandler') -> tuple[dict[str, Airdrop], dict[str, list[str]]]:  # noqa: E501
    """Fetches airdrop metadata from the rotki/data repository. If it's not cached, parses them,
    and returns them in two parts: a dict of Airdrop instances and a dict of POAP airdrops data.

    May raise - RemoteError if the request fails or metadata is invalid.
    """
    airdrops_data = None
    with GlobalDBHandler().conn.read_ctx() as cursor:
        airdrops_metadata_cached_at = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.AIRDROPS_METADATA,),
        )
        if ts_now() - airdrops_metadata_cached_at < HOUR_IN_SECONDS * 12:
            airdrops_metadata_cache = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.AIRDROPS_METADATA,),
            )
            if airdrops_metadata_cache is not None:
                airdrops_data = jsonloads_dict(airdrops_metadata_cache)  # get cached response

    if airdrops_data is None:  # query fresh data
        try:
            airdrops_data = requests.get(url=AIRDROPS_INDEX, timeout=CachedSettings().get_timeout_tuple()).json()  # noqa: E501
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Airdrops Index request failed due to {e!s}') from e

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.AIRDROPS_METADATA,),
                value=json.dumps(airdrops_data),
            )

    return (
        _parse_airdrops(database=database, airdrops_data=airdrops_data['airdrops']),
        airdrops_data['poap_airdrops'],
    )


def get_airdrop_data(airdrop_csv_path: str, name: str, parent_data_dir: Path) -> Iterator[list[str]]:  # noqa: E501
    airdrops_dir = parent_data_dir / 'airdrops'
    airdrops_dir.mkdir(parents=True, exist_ok=True)
    filename = airdrops_dir / f'{name}.csv'
    if not filename.is_file():
        # if not cached, get it from the gist
        try:
            response = requests.get(url=airdrop_csv_path, timeout=(30, 100))  # a large read timeout is necessary because the queried data is quite large  # noqa: E501
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Airdrops Gist request failed due to {e!s}') from e
        content = response.text
        try:
            if (
                not csv.Sniffer().has_header(content) or
                len(response.content) < SMALLEST_AIRDROP_SIZE
            ):
                raise csv.Error
            with open(filename, 'w', encoding='utf8') as f:
                f.write(content)
        except csv.Error as e:
            log.debug(f'airdrop file {filename} contains invalid data {content}')
            raise RemoteError(
                f'File {filename} contains invalid data. Check logs.',
            ) from e
    # Verify the CSV file
    with open(filename, encoding='utf8') as csvfile:
        iterator = csv.reader(csvfile)
        next(iterator)  # skip header
        yield from iterator


def get_poap_airdrop_data(poap_airdrop_path: str, name: str, data_dir: Path) -> dict[str, Any]:
    airdrops_dir = data_dir / 'airdrops_poap'
    airdrops_dir.mkdir(parents=True, exist_ok=True)
    filename = airdrops_dir / f'{name}.json'
    if not filename.is_file():
        # if not cached, get it from the gist
        try:
            request = requests.get(url=f'{AIRDROPS_REPO_BASE}/{poap_airdrop_path}', timeout=CachedSettings().get_timeout_tuple())  # noqa: E501
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'POAP airdrops Gist request failed due to {e!s}') from e

        try:
            json_data = jsonloads_dict(request.content.decode('utf-8'))
        except JSONDecodeError as e:
            raise RemoteError(f'POAP airdrops Gist contains an invalid JSON {e!s}') from e

        with open(filename, 'w', encoding='utf8') as outfile:
            outfile.write(rlk_jsondumps(json_data))

    return jsonloads_dict(Path(filename).read_text(encoding='utf8'))


def calculate_claimed_airdrops(
        airdrop_data: Sequence[AirdropClaimEventQueryParams],
        database: DBHandler,
) -> Sequence[tuple[ChecksumEvmAddress, str, FVal]]:
    """Calculates which of the given airdrops have been claimed.
    It does so by checking if there is a claim history event in the database
    that matches the airdrop data (address, asset and amount). It returns a list
    of tuples with the airdrop data for which a claim event was found."""
    if len(airdrop_data) == 0:
        return []

    query_parts, bindings = [], []
    for airdrop_info in airdrop_data:
        amount = airdrop_info.tolerance.value
        half_range = airdrop_info.tolerance.tolerance / 2
        query_parts.append('(events.type=? AND events.subtype=? AND events.location_label=? AND events.asset=? AND CAST(events.amount AS REAL) BETWEEN ? AND ?)')  # noqa: E501
        bindings.extend(
            [
                airdrop_info.event_type.serialize(),
                airdrop_info.event_subtype.serialize(),
                airdrop_info.location_label,
                airdrop_info.asset.serialize(),
                str(amount - half_range),
                str(amount + half_range),
            ],
        )

    query_part = ' OR '.join(query_parts)
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT events.location_label, events.asset, events.amount '
            f'FROM history_events AS events WHERE {query_part}',
            tuple(bindings),
        ).fetchall()


def check_airdrops(
        addresses: Sequence[ChecksumEvmAddress],
        database: DBHandler,
        tolerance_for_amount_check: FVal = ZERO,
) -> dict[ChecksumEvmAddress, dict]:
    """Checks airdrop data for the given list of ethereum addresses

    May raise:
        - RemoteError if the remote request fails
    """
    found_data: dict[ChecksumEvmAddress, dict] = defaultdict(lambda: defaultdict(dict))
    parent_data_dir = database.user_data_dir.parent
    airdrop_tuples = []
    current_time = ts_now()
    airdrops, poap_airdrops = fetch_airdrops_metadata(database=database)

    for protocol_name, airdrop_data in airdrops.items():
        if airdrop_data.cutoff_time is not None and current_time > airdrop_data.cutoff_time:
            log.debug(f'Skipping {protocol_name} airdrop since it is not claimable after {airdrop_data.cutoff_time}')  # noqa: E501
            continue

        # In the shutter airdrop the claim of the vested SHU is decoded as informational/none
        if protocol_name == 'shutter':
            claim_event_type = HistoryEventType.INFORMATIONAL
            claim_event_subtype = HistoryEventSubType.NONE
        else:
            claim_event_type = HistoryEventType.RECEIVE
            claim_event_subtype = HistoryEventSubType.AIRDROP

        for row in get_airdrop_data(airdrop_data.csv_path, protocol_name, parent_data_dir):
            if len(row) < 2:
                raise RemoteError(
                    f'Airdrop CSV for {protocol_name} contains an invalid row: {row}',
                )
            addr, amount, *_ = row
            # not doing to_checksum_address() here since the file addresses are checksummed
            # and doing to_checksum_address() so many times hits performance
            if protocol_name in {
                'cornichon',
                'tornado',
                'grain',
                'lido',
                'sdl',
                'cow_mainnet',
                'cow_gnosis',
            }:
                amount = token_normalized_value_decimals(int(amount), 18)  # type: ignore
            if addr in addresses:
                found_data[addr][protocol_name] = {  # type: ignore
                    'amount': str(amount),
                    'asset': airdrop_data.asset,
                    'link': airdrop_data[2],
                    'claimed': False,
                }
                airdrop_tuples.append(
                    AirdropClaimEventQueryParams(
                        event_type=claim_event_type,
                        event_subtype=claim_event_subtype,
                        location_label=string_to_evm_address(addr),
                        asset=airdrop_data.asset,
                        tolerance=FValWithTolerance(
                            value=FVal(amount),
                            tolerance=tolerance_for_amount_check,
                        ),
                    ),
                )

    asset_to_protocol = {item[1].identifier: protocol for protocol, item in airdrops.items()}
    claim_events_tuple = calculate_claimed_airdrops(
        airdrop_data=airdrop_tuples,
        database=database,
    )
    for event_tuple in claim_events_tuple:
        found_data[event_tuple[0]][asset_to_protocol[event_tuple[1]]]['claimed'] = True

    for protocol_name, poap_airdrop_data in poap_airdrops.items():
        data_dict = get_poap_airdrop_data(poap_airdrop_data[0], protocol_name, parent_data_dir)
        for addr, assets in data_dict.items():
            # not doing to_checksum_address() here since the file addresses are checksummed
            # and doing to_checksum_address() so many times hits performance
            if addr in addresses:
                if 'poap' not in found_data[addr]:  # type: ignore[index]
                    found_data[addr]['poap'] = []  # type: ignore[index]

                found_data[addr]['poap'].append({  # type: ignore[index]
                    'event': protocol_name,
                    'assets': assets,
                    'link': poap_airdrop_data[1],
                    'name': poap_airdrop_data[2],
                })

    return dict(found_data)
