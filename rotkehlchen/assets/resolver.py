import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

from rotkehlchen.errors import UnknownAsset, ModuleInitializationFailure
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.typing import AssetData, AssetType

log = logging.getLogger(__name__)

# this needs to also be reflected in the globaldb enum.
# but we should also aim to get rid of it
asset_type_mapping = {
    'fiat': AssetType.FIAT,
    'own chain': AssetType.OWN_CHAIN,
    'ethereum token': AssetType.ETHEREUM_TOKEN,
    'omni token': AssetType.OMNI_TOKEN,
    'neo token': AssetType.NEO_TOKEN,
    'counterparty token': AssetType.COUNTERPARTY_TOKEN,
    'bitshares token': AssetType.BITSHARES_TOKEN,
    'ardor token': AssetType.ARDOR_TOKEN,
    'nxt token': AssetType.NXT_TOKEN,
    'ubiq token': AssetType.UBIQ_TOKEN,
    'nubits token': AssetType.NUBITS_TOKEN,
    'burst token': AssetType.BURST_TOKEN,
    'waves token': AssetType.WAVES_TOKEN,
    'qtum token': AssetType.QTUM_TOKEN,
    'stellar token': AssetType.STELLAR_TOKEN,
    'tron token': AssetType.TRON_TOKEN,
    'ontology token': AssetType.ONTOLOGY_TOKEN,
    'vechain token': AssetType.VECHAIN_TOKEN,
    'binance token': AssetType.BINANCE_TOKEN,
    'eos token': AssetType.EOS_TOKEN,
    'fusion token': AssetType.FUSION_TOKEN,
    'luniverse token': AssetType.LUNIVERSE_TOKEN,
    'other': AssetType.OTHER,
}


def _get_latest_assets(data_directory: Path) -> Tuple[bool, Path]:
    """Gets the latest assets either locally or from the remote

    Checks the remote (github) and if there is a newer file there it pulls it,
    saves it and its md5 hash locally and returns the new assets..

    If there is no new file (same hash) or if there is any problem contacting the remote
    then nothing is done.

    Returns a tuple. First part is a boolean returning True if there is a
    new file downloaded and False otherwise.
    Second part is the directory path of the all_assets.json to prime the db from
    """
    root_dir = Path(__file__).resolve().parent.parent
    downloaded_dir = data_directory / 'assets'
    builtin_dir = root_dir / 'data'
    our_downloaded_meta = downloaded_dir / 'all_assets.meta'
    our_builtin_meta = builtin_dir / 'all_assets.meta'
    try:
        response = requests.get('https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.meta')  # noqa: E501
        remote_meta = response.json()

        with open(our_builtin_meta, 'r') as f:
            builtin_meta = json.loads(f.read())

        downloaded_meta = None
        if our_downloaded_meta.is_file():
            with open(our_downloaded_meta, 'r') as f:
                downloaded_meta = json.loads(f.read())

        if builtin_meta['version'] >= remote_meta['version']:
            log.debug(
                f'Builtin assets file has version {builtin_meta["version"]} greater than '
                f'the remote one {remote_meta["version"]}. Keeping the built in.',
            )
            return False, builtin_dir

        if downloaded_meta and downloaded_meta['version'] > remote_meta['version']:
            log.debug(
                f'Downloaded assets file has version {downloaded_meta["version"]} greater than '
                f'the remote one {remote_meta["version"]}. Keeping the downloaded one.',
            )
            return False, downloaded_dir

        if remote_meta['version'] > builtin_meta['version']:
            # we need to download and save the new assets from github
            response = requests.get('https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.json')  # noqa: E501
            remote_asset_data = response.text

            # Make sure directory exists
            (data_directory / 'assets').mkdir(parents=True, exist_ok=True)
            # Write the files
            with open(data_directory / 'assets' / 'all_assets.meta', 'w') as f:
                f.write(json.dumps(remote_meta))
            with open(data_directory / 'assets' / 'all_assets.json', 'w') as f:
                f.write(remote_asset_data)

            log.debug(
                f'Found newer remote assets file with version: {remote_meta["version"]} '
                f' and {remote_meta["md5"]} md5 hash. Replaced local file',
            )
            return True, downloaded_dir

        # else, same as all error cases use the built-in one
    except (requests.exceptions.RequestException, KeyError, json.decoder.JSONDecodeError):
        pass

    return False, builtin_dir


def _maybe_prime_globaldb(assets_dir: Path) -> None:
    """Maybe prime globaldb with assets from all_assets.json of the given directory

    May raise:
    - OSError if a file can't be found
    - KeyError if a key is missing from any of the expected dicts (should not happen)
    """
    with open(assets_dir / 'all_assets.meta', 'r') as f:
        meta_data = json.loads(f.read())

    last_version = GlobalDBHandler().get_setting_value('last_assets_json_version', 0)
    if last_version >= meta_data['version']:
        # also delete the all assets_cache once priming is done
        AssetResolver().clean_asset_json_cache()
        return

    with open(assets_dir / 'all_assets.json', 'r') as f:
        assets = json.loads(f.read())

    ethereum_tokens = []
    other_assets = []
    for asset_id, entry in assets.items():
        if asset_id == 'XD':
            continue  # https://github.com/rotki/rotki/issues/2503
        entry['identifier'] = asset_id
        asset_type = asset_type_mapping.get(entry['type'], None)
        if not asset_type:
            log.error(
                f'During priming GlobalDB skipping asset with id {asset_id} '
                f'due to unknown type {entry["type"]}',
            )
            continue
        entry['type'] = asset_type
        if asset_type == AssetType.ETHEREUM_TOKEN:
            ethereum_tokens.append(entry)
        else:
            other_assets.append(entry)

    GlobalDBHandler().add_all_assets_from_json(ethereum_tokens=ethereum_tokens, other_assets=other_assets)  # noqa: E501

    # in the end set the last version primed
    GlobalDBHandler().add_setting_value('last_assets_json_version', meta_data['version'])
    # also delete the all assets_cache once priming is done
    AssetResolver().clean_asset_json_cache()
    return


def _attempt_initialization(
        data_directory: Optional[Path],
        read_assets: bool,
) -> Tuple[bool, Optional[Dict[str, AssetData]]]:
    """Reads the asset data either from builtin data or from the remote

    1. If it's the very first time data is initialized (and data directory is not given)
    then just get assets from the builtin file
    2. If data directory is still not given but we have some saved assets return them directly
    3. If data directory is given then we can finally do the comparison of local
    saved and builtin file with the remote and return the most recent assets.

    Returns a Tuple. First part is a boolean denoting if the remote check happened or not.
    If it did then we have the most recent assets.
    Second part contains the built in all_assets.json file in memory mapping loaded
    only at the start.
    """
    if not data_directory:
        if read_assets:
            # Do not read the all_assets file again if it has been already read
            return False, None

        # First initialization. Read the builtin all_assets.json and use it for asset
        # resolution until the DB is primed
        root_dir = Path(__file__).resolve().parent.parent
        assets_data_dir = root_dir / 'data'
        with open(assets_data_dir / 'all_assets.json', 'r') as f:
            assets = json.loads(f.read())

        all_assets_mapping = {}
        for asset_id, data in assets.items():
            asset_type = asset_type_mapping.get(data['type'], None)
            if not asset_type:
                log.error(
                    f'At initial load of asset.json, skipping asset with id '
                    f'{asset_id} due to unknown type {data["type"]}',
                )
                continue

            all_assets_mapping[asset_id] = AssetData(
                identifier=asset_id,
                symbol=data['symbol'],
                name=data['name'],
                asset_type=asset_type,
                started=data.get('started', None),
                forked=data.get('forked', None),
                swapped_for=data.get('swapped_for', None),
                ethereum_address=data.get('ethereum_address', None),
                decimals=data.get('ethereum_token_decimals', None),
                cryptocompare=data.get('cryptocompare', None),
                coingecko=data.get('coingecko', None),
                protocol=data.get('protocol', None),
            )
        return False, all_assets_mapping

    # else we got the data directory so we can finally do the remote check and prime the db
    _, assets_dir = _get_latest_assets(data_directory)
    _maybe_prime_globaldb(assets_dir=assets_dir)
    return True, None


class AssetResolver():
    __instance = None
    remote_check_happened: bool = False
    # all_assets.json loaded in memory until the DB is primed
    all_assets: Dict[str, AssetData] = {}
    # A cache so that the DB is not hit every time
    assets_cache: Dict[str, AssetData] = {}

    def __new__(
            cls,
            data_directory: Path = None,
    ) -> 'AssetResolver':
        """Lazily initializes AssetResolver

        As long as it's called without a data_directory path it uses the builtin
        all_assets file loaded in memory.

        Once a data directory is given it attempts to see if a
        newer file exists on the remote and uses that. Also primes the DB with
        the assets of the newest file if needed. Once that's done the remote
        check flag is set to True.

        From that point on all calls to AssetResolver() return the same data and
        use the DB.
        """
        if AssetResolver.__instance is not None:
            if AssetResolver.__instance.remote_check_happened:  # type: ignore
                return AssetResolver.__instance

            # else we still have not performed the remote check
            check_happened, _ = _attempt_initialization(
                data_directory=data_directory,
                read_assets=True,
            )
        else:
            # first initialization
            check_happened, all_assets_mapping = _attempt_initialization(
                data_directory=data_directory,
                read_assets=False,
            )
            AssetResolver.__instance = object.__new__(cls)
            if not check_happened:  # check_happened can be true after first init only for tests
                assert all_assets_mapping is not None, 'should have read built-in all_assets.json'
            AssetResolver.__instance.all_assets = all_assets_mapping

        AssetResolver.__instance.remote_check_happened = check_happened

        return AssetResolver.__instance

    @staticmethod
    def clean_asset_json_cache() -> None:
        assert AssetResolver.__instance is not None, 'when cleaning the cache instance should be set'  # noqa: E501
        del AssetResolver.__instance.all_assets
        AssetResolver.__instance.all_assets = None

    @staticmethod
    def get_asset_data(
            asset_identifier: str,
            form_with_incomplete_data: bool = False,
    ) -> AssetData:
        """Get all asset data for a valid asset identifier

        Raises UnknownAsset if no data can be found
        """
        instance = AssetResolver()
        # attempt read from memory cache -- always lower
        cached_data = instance.assets_cache.get(asset_identifier.lower(), None)
        if cached_data is not None:
            return cached_data

        check_json = False
        try:
            dbinstance = GlobalDBHandler()
            if dbinstance.get_setting_value('last_assets_json_version', 0) == 0:
                check_json = True
        except ModuleInitializationFailure:
            check_json = True

        if check_json:  # still need to resolve out of the in memory all_assets.json
            if instance.all_assets is None:
                raise AssertionError(
                    'We need to check all_assets.json and cached data has been deleted',
                )

            result = instance.all_assets.get(asset_identifier, None)
            if result is None:
                raise UnknownAsset(asset_identifier)
            return result

        # At this point we can use the global DB
        asset_data = dbinstance.get_asset_data(asset_identifier, form_with_incomplete_data)
        if asset_data is None:
            raise UnknownAsset(asset_identifier)

        # save in the memory cache -- always lower
        instance.assets_cache[asset_identifier.lower()] = asset_data
        return asset_data
