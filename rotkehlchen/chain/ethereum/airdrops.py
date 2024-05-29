import csv
import logging
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, Final, NamedTuple, cast

import requests
from requests import Response

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.misc import AIRDROPSDIR_NAME, AIRDROPSPOAPDIR_NAME, APPDIR_NAME
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_value,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_int
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, FValWithTolerance, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import is_production, ts_now
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SMALLEST_AIRDROP_SIZE: Final = 20900
AIRDROPS_REPO_BASE: Final = f'https://raw.githubusercontent.com/rotki/data/{"main" if is_production() else "develop"}'  # noqa: E501
AIRDROPS_INDEX: Final = f'{AIRDROPS_REPO_BASE}/airdrops/index_v2.json'
ETAG_CACHE_KEY: Final = 'ETag'
JSON_PATH_SEPARATOR_API_AIRDROPS: Final = '/'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, kw_only=True)  # noqa: E501
class Airdrop:
    """Airdrop class for representing airdrop data.

    This contains the definition of the Airdrop class, which is used to represent
    individual airdrops along with their associated data, such as URL, token address,
    website URL, name, and icon filename.
    """
    asset: CryptoAsset
    url: str
    name: str
    icon: str
    icon_url: str | None = None
    cutoff_time: Timestamp | None = None
    has_decoder: bool = True


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, kw_only=True)  # noqa: E501
class CSVAirdrop(Airdrop):
    """Airdrops that provide CSV files and we can use to query claimable amounts"""
    csv_path: str
    csv_hash: str


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False, kw_only=True)  # noqa: E501
class AirdropAPIData(Airdrop):
    """Airdrops that use a remote url to determine the amount claimable.
    Used when CSVs aren't available
    """
    api_url: str
    amount_path: str  # json keys separated by `/` that point to the amount that needs to be extracted  # noqa: E501


class AirdropClaimEventQueryParams(NamedTuple):
    """Params used in the SQL query to detect as claimed an airdrop"""
    event_type: HistoryEventType
    event_subtype: HistoryEventSubType
    location_label: ChecksumEvmAddress
    asset: CryptoAsset
    tolerance: FValWithTolerance


def _enrich_user_airdrop_data(
        user_data: dict[str, Any],
        protocol_name: str,
        airdrop_data: Airdrop,
) -> None:
    """Modify user_data to add information about icons"""
    if airdrop_data.icon_url is not None:
        user_data[protocol_name]['icon_url'] = airdrop_data.icon_url


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
                        coingecko=new_asset_data.get('coingecko'),
                        cryptocompare=new_asset_data.get('cryptocompare'),
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

            # combining the base data repo url for main/develop with the path to the icon in that repo  # noqa: E501
            icon_url = f"{AIRDROPS_REPO_BASE}/{airdrop_data['icon_path']}" if 'icon_path' in airdrop_data else None  # noqa: E501
            if 'csv_path' in airdrop_data:
                new_airdrop: Airdrop = CSVAirdrop(
                    asset=crypto_asset,
                    # combining the base data repo url for main/develop with the path to the CSV in that repo  # noqa: E501
                    csv_path=f"{AIRDROPS_REPO_BASE}/{airdrop_data['csv_path']}",
                    csv_hash=airdrop_data['csv_hash'],
                    url=airdrop_data['url'],
                    name=airdrop_data['name'],
                    icon=airdrop_data['icon'],
                    icon_url=icon_url,
                    cutoff_time=airdrop_data.get('cutoff_time'),
                    has_decoder=airdrop_data.get('has_decoder', True),
                )
            elif 'api_url' in airdrop_data:
                new_airdrop = AirdropAPIData(
                    asset=crypto_asset,
                    api_url=airdrop_data['api_url'],
                    amount_path=airdrop_data['amount_path'],
                    url=airdrop_data['url'],
                    name=airdrop_data['name'],
                    icon=airdrop_data['icon'],
                    icon_url=icon_url,
                    cutoff_time=airdrop_data.get('cutoff_time'),
                    has_decoder=airdrop_data.get('has_decoder', True),
                )
            else:
                log.error(f'Invalid CSV airdrop format found {airdrop_data}. Skipping')
                continue

            airdrops[protocol_name] = new_airdrop
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
        headers = {}
        if (cached_etag := globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.AIRDROPS_HASH, ETAG_CACHE_KEY),
        )) is not None:
            headers['If-None-Match'] = cached_etag.encode('utf-8')

        try:
            remote_metadata_res = requests.get(
                url=AIRDROPS_INDEX,
                timeout=CachedSettings().get_timeout_tuple(),
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Airdrops Index request failed due to {e!s}') from e

        if remote_metadata_res.status_code == HTTPStatus.NOT_MODIFIED:  # index is not modified, use cached index  # noqa: E501
            airdrops_metadata_cache = globaldb_get_unique_cache_value(
                cursor=cursor,
                key_parts=(CacheType.AIRDROPS_METADATA,),
            )
            if airdrops_metadata_cache is not None:
                airdrops_data = jsonloads_dict(airdrops_metadata_cache)  # get cached response

    if airdrops_data is None:  # index has been modified, save new index
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.AIRDROPS_HASH, ETAG_CACHE_KEY),
                value=remote_metadata_res.headers[ETAG_CACHE_KEY],
            )
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.AIRDROPS_METADATA,),
                value=remote_metadata_res.text,
            )
            try:
                airdrops_data = remote_metadata_res.json()
            except JSONDecodeError as e:
                raise RemoteError(f'Airdrops Index is not valid JSON {e!s}') from e

    return (
        _parse_airdrops(database=database, airdrops_data=airdrops_data['airdrops']),
        airdrops_data['poap_airdrops'],
    )


def _maybe_get_updated_file(
        data_dir: Path,
        name: str,
        file_hash: str,
        remote_url: str,
        process_response: Callable[[Response, Path], None],
) -> Path:
    """Downloads the file if cached hash is different and returns its path."""
    data_dir.mkdir(parents=True, exist_ok=True)
    filename = data_dir / f'{name}'

    with GlobalDBHandler().conn.read_ctx() as cursor:
        if (existing_csv_hash := globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(CacheType.AIRDROPS_HASH, name),
        )) != file_hash:
            log.info(
                f'Found a new {name} airdrop file hash: {file_hash}. '
                f'Removing the old file with hash: {existing_csv_hash}, and downloading new one.',
            )
            filename.unlink(missing_ok=True)

    if not filename.is_file():
        # if not cached, get it from the remote data repo
        try:
            response = requests.get(url=remote_url, timeout=(30, 100))  # a large read timeout is necessary because the queried data is quite large  # noqa: E501
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Airdrops CSV request failed due to {e!s}') from e
        process_response(response, filename)

        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            globaldb_set_unique_cache_value(
                write_cursor=write_cursor,
                key_parts=(CacheType.AIRDROPS_HASH, name),
                value=file_hash,
            )

    return filename


def get_airdrop_data(airdrop_data: CSVAirdrop, name: str, data_dir: Path) -> Iterator[list[str]]:
    """Yields the rows from airdrop's CSV file after downloading it locally for the first time.
    If a new CSV is found in the index, it will be downloaded again to update the local CSV file
    and yield new data."""
    airdrops_dir = data_dir / APPDIR_NAME / AIRDROPSDIR_NAME

    def _process_csv(response: Response, filename: Path) -> None:
        try:
            if (
                not csv.Sniffer().has_header(response.text) or
                len(response.content) < SMALLEST_AIRDROP_SIZE
            ):
                raise csv.Error

            filename.write_text(response.text, encoding='utf8')

        except csv.Error as e:
            log.debug(f'airdrop file {filename} contains invalid data {response.text}')
            raise RemoteError(
                f'File {filename} contains invalid data. Check logs.',
            ) from e

    filename = _maybe_get_updated_file(
        data_dir=airdrops_dir,
        file_hash=airdrop_data.csv_hash,
        name=f'{name}.csv',
        remote_url=airdrop_data.csv_path,
        process_response=_process_csv,
    )

    # Verify the CSV file
    with open(filename, encoding='utf8') as csvfile:
        iterator = csv.reader(csvfile)
        next(iterator)  # skip header
        yield from iterator


def get_poap_airdrop_data(airdrop_data: list[str], name: str, data_dir: Path) -> dict[str, Any]:
    """Returns a dictionary of POAP airdrop data after downloading it locally for the first time.
    If a new JSON is found in the index, it will be downloaded again to update the local JSON file
    and return its data."""
    airdrops_dir = data_dir / APPDIR_NAME / AIRDROPSPOAPDIR_NAME

    def _process_json(response: Response, filename: Path) -> None:
        try:
            json_data = jsonloads_dict(response.content.decode('utf-8'))
        except JSONDecodeError as e:
            log.error(f"POAP airdrop {name}'s JSON is invalid {e!s}")
            json_data = {}

        filename.write_text(rlk_jsondumps(json_data), encoding='utf8')

    filename = _maybe_get_updated_file(
        data_dir=airdrops_dir,
        file_hash=airdrop_data[3],
        name=f'{name}.json',
        remote_url=f'{AIRDROPS_REPO_BASE}/{airdrop_data[0]}',
        process_response=_process_json,
    )

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


def process_airdrop_with_api_data(
        addresses: Sequence[ChecksumEvmAddress],
        airdrop_data: AirdropAPIData,
        protocol_name: str,
        tolerance_for_amount_check: FVal,
) -> tuple[list[AirdropClaimEventQueryParams], dict[ChecksumEvmAddress, dict]]:
    """Query the airdrops that have information available only by consuming APIs
    with the user addresses.

    It returns a list of `AirdropClaimEventQueryParams` used to filter the history
    events with the expected amount received and the combination of types and a mapping
    with information about the asset for the airdrop, the amount, deadlines and other
    relevant details.
    """
    timeout_tuple = CachedSettings().get_timeout_tuple()
    found_data: dict[ChecksumEvmAddress, dict] = defaultdict(lambda: defaultdict(dict))
    temp_airdrop_tuples = []
    for address in addresses:
        try:
            response = requests.get(
                url=airdrop_data.api_url.format(address=address),
                timeout=timeout_tuple,
            )
            data: dict[str, Any] = response.json()
        except requests.exceptions.RequestException as e:
            log.error(
                f'Failed to query {protocol_name} airdrop API for address {address} due to {e}',
            )
            continue

        if response.status_code >= 400:
            log.error(
                f'Error response from {protocol_name} API for {address}: {data}. '
                'Skipping airdrop',
            )
            continue

        try:
            token_num = data
            for key in airdrop_data.amount_path.split(JSON_PATH_SEPARATOR_API_AIRDROPS):
                token_num = token_num[key]
        except KeyError as e:
            log.error(
                f'Could not find {airdrop_data.amount_path} in {data} for {protocol_name}. '
                f'Missing key {e}. Skipping',
            )
            continue

        try:
            amount = deserialize_int(cast(int, token_num))
        except DeserializationError as e:
            log.error(f'Failed to read amount from {protocol_name} API: {e}. Skipping')
            continue

        if amount == 0:
            continue

        found_data[address][protocol_name] = {
            'amount': str(amount),
            'asset': airdrop_data.asset,
            'link': airdrop_data.url,
            'claimed': False,
            'has_decoder': airdrop_data.has_decoder,
        }
        _enrich_user_airdrop_data(
            user_data=found_data[address],
            protocol_name=protocol_name,
            airdrop_data=airdrop_data,
        )

        temp_airdrop_tuples.append(
            AirdropClaimEventQueryParams(
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                location_label=address,
                asset=airdrop_data.asset,
                tolerance=FValWithTolerance(
                    value=FVal(amount),
                    tolerance=tolerance_for_amount_check,
                ),
            ),
        )

    return temp_airdrop_tuples, found_data


def _process_csv_airdrop(
        msg_aggregator: MessagesAggregator,
        addresses: Sequence[ChecksumEvmAddress],
        data_dir: Path,
        airdrop_data: CSVAirdrop,
        protocol_name: str,
        tolerance_for_amount_check: FVal,
        current_time: Timestamp,
) -> tuple[list[AirdropClaimEventQueryParams], dict[ChecksumEvmAddress, dict]]:
    """Process csv to find the addresses that have a claimable amount.

    It returns a list of `AirdropClaimEventQueryParams` used to filter the history
    events with the expected amount received and the combination of types and a mapping
    with information about the asset for the airdrop, the amount, deadlines and other
    relevant details.
    """
    if airdrop_data.cutoff_time is not None and current_time > airdrop_data.cutoff_time:
        log.debug(f'Skipping {protocol_name} airdrop since it is not claimable after {airdrop_data.cutoff_time}')  # noqa: E501
        return [], {}

    # In the shutter airdrop the claim of the vested SHU is decoded as informational/none
    if protocol_name == 'shutter':
        claim_event_type = HistoryEventType.INFORMATIONAL
        claim_event_subtype = HistoryEventSubType.NONE
    else:
        claim_event_type = HistoryEventType.RECEIVE
        claim_event_subtype = HistoryEventSubType.AIRDROP

    # temporarily store this protocol's data here
    temp_found_data: dict[ChecksumEvmAddress, dict] = defaultdict(lambda: defaultdict(dict))
    temp_airdrop_tuples = []
    for row in get_airdrop_data(airdrop_data, protocol_name, data_dir):
        if len(row) < 2:
            msg_aggregator.add_warning(f'Skipping airdrop CSV for {protocol_name} because it contains an invalid row: {row}')  # noqa: E501
            break
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
            addr = string_to_evm_address(addr)
            temp_found_data[addr][protocol_name] = {
                'amount': str(amount),
                'asset': airdrop_data.asset,
                'link': airdrop_data.url,
                'claimed': False,
                'has_decoder': airdrop_data.has_decoder,
            }
            _enrich_user_airdrop_data(
                user_data=temp_found_data[addr],
                protocol_name=protocol_name,
                airdrop_data=airdrop_data,
            )
            temp_airdrop_tuples.append(
                AirdropClaimEventQueryParams(
                    event_type=claim_event_type,
                    event_subtype=claim_event_subtype,
                    location_label=addr,
                    asset=airdrop_data.asset,
                    tolerance=FValWithTolerance(
                        value=FVal(amount),
                        tolerance=tolerance_for_amount_check,
                    ),
                ),
            )
    else:  # if all rows are valid, return the information
        return temp_airdrop_tuples, temp_found_data

    return [], {}


def check_airdrops(
        msg_aggregator: MessagesAggregator,
        addresses: Sequence[ChecksumEvmAddress],
        database: DBHandler,
        data_dir: Path,
        tolerance_for_amount_check: FVal = ZERO,
) -> dict[ChecksumEvmAddress, dict]:
    """Checks airdrop data for the given list of ethereum addresses

    May raise:
        - RemoteError if the remote request fails
    """
    found_data: dict[ChecksumEvmAddress, dict] = defaultdict(lambda: defaultdict(dict))
    airdrop_tuples = []
    current_time = ts_now()
    airdrops, poap_airdrops = fetch_airdrops_metadata(database=database)

    for protocol_name, airdrop_data in airdrops.items():
        if isinstance(airdrop_data, CSVAirdrop):
            temp_airdrop_tuples, temp_found_data = _process_csv_airdrop(
                msg_aggregator=msg_aggregator,
                addresses=addresses,
                data_dir=data_dir,
                airdrop_data=airdrop_data,
                protocol_name=protocol_name,
                tolerance_for_amount_check=tolerance_for_amount_check,
                current_time=current_time,
            )
        else:  # airdrop with api metadata AirdropAPIData
            temp_airdrop_tuples, temp_found_data = process_airdrop_with_api_data(
                addresses=addresses,
                airdrop_data=airdrop_data,  # type: ignore
                protocol_name=protocol_name,
                tolerance_for_amount_check=tolerance_for_amount_check,
            )

        airdrop_tuples.extend(temp_airdrop_tuples)
        for temp_addr, data in temp_found_data.items():
            found_data[temp_addr].update(data)

    asset_to_protocol = {item.asset.identifier: protocol for protocol, item in airdrops.items()}
    claim_events_tuple = calculate_claimed_airdrops(
        airdrop_data=airdrop_tuples,
        database=database,
    )
    for event_tuple in claim_events_tuple:
        found_data[event_tuple[0]][asset_to_protocol[event_tuple[1]]]['claimed'] = True

    for protocol_name, poap_airdrop_data in poap_airdrops.items():
        data_dict = get_poap_airdrop_data(poap_airdrop_data, protocol_name, data_dir)
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
