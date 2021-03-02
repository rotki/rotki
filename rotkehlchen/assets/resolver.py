import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import requests
from eth_utils.address import to_checksum_address

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE, ETHEREUM_DIRECTIVE_LENGTH
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.typing import AssetData, AssetType, ChecksumEthAddress, EthTokenInfo

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.typing import CustomEthereumToken

log = logging.getLogger(__name__)

asset_type_mapping = {
    'fiat': AssetType.FIAT,
    'own chain': AssetType.OWN_CHAIN,
    'ethereum token and own chain': AssetType.OWN_CHAIN,
    'ethereum token and more': AssetType.ETH_TOKEN_AND_MORE,
    'ethereum token': AssetType.ETH_TOKEN,
    'omni token': AssetType.OMNI_TOKEN,
    'neo token': AssetType.NEO_TOKEN,
    'counterparty token': AssetType.XCP_TOKEN,
    'bitshares token': AssetType.BTS_TOKEN,
    'ardor token': AssetType.ARDOR_TOKEN,
    'nxt token': AssetType.NXT_TOKEN,
    'Ubiq token': AssetType.UBIQ_TOKEN,
    'Nubits token': AssetType.NUBITS_TOKEN,
    'Burst token': AssetType.BURST_TOKEN,
    'waves token': AssetType.WAVES_TOKEN,
    'qtum token': AssetType.QTUM_TOKEN,
    'stellar token': AssetType.STELLAR_TOKEN,
    'tron token': AssetType.TRON_TOKEN,
    'ontology token': AssetType.ONTOLOGY_TOKEN,
    'exchange specific': AssetType.EXCHANGE_SPECIFIC,
    'vechain token': AssetType.VECHAIN_TOKEN,
    'binance token': AssetType.BINANCE_TOKEN,
    'eos token': AssetType.EOS_TOKEN,
    'fusion token': AssetType.FUSION_TOKEN,
    'luniverse token': AssetType.LUNIVERSE_TOKEN,
}


def _extract_custom_token_data(asset_identifier: str) -> Optional['CustomEthereumToken']:
    try:
        address = to_checksum_address(asset_identifier[ETHEREUM_DIRECTIVE_LENGTH:])
    except (ValueError, TypeError):
        log.debug(f'Could not extract ethereum address from {asset_identifier}')
        return None

    return GlobalDBHandler().get_ethereum_token(address=address)


def _get_latest_assets(data_directory: Path) -> Dict[str, Any]:
    """Gets the latest assets either locally or from the remote

    Checks the remote (github) and if there is a newer file there it pulls it,
    saves it and its md5 hash locally and returns the new assets.

    If there is no new file (same hash) or if there is any problem contacting the remote
    then the builtin assets file is used.
    """
    root_dir = Path(__file__).resolve().parent.parent
    our_downloaded_meta = data_directory / 'assets' / 'all_assets.meta'
    our_builtin_meta = root_dir / 'data' / 'all_assets.meta'
    assets_file = root_dir / 'data' / 'all_assets.json'
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
            assets_file = root_dir / 'data' / 'all_assets.json'
            log.debug(
                f'Builtin assets file has version {builtin_meta["version"]} greater than '
                f'the remote one {remote_meta["version"]}. Keeping the built in.',
            )
        elif downloaded_meta and downloaded_meta['version'] > remote_meta['version']:
            assets_file = data_directory / 'assets' / 'all_assets.json'
            log.debug(
                f'Downloaded assets file has version {downloaded_meta["version"]} greater than '
                f'the remote one {remote_meta["version"]}. Keeping the downloaded one.',
            )
        elif remote_meta['version'] > builtin_meta['version']:
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
            return json.loads(remote_asset_data)

        # else, same as all error cases use the built-in one
    except (requests.exceptions.RequestException, KeyError, json.decoder.JSONDecodeError):
        pass

    with open(assets_file, 'r') as f:
        return json.loads(f.read())


def _attempt_initialization(
        data_directory: Optional[Path],
        saved_assets: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], bool]:
    """Reads the asset data either from builtin data or from the remote

    1. If it's the very first time data is initialized (and data directory is not given)
    then just get assets from the builtin file
    2. If data directory is still not given but we have some saved assets return them directly
    3. If data directory is given then we can finally do the comparison of local
    saved and builtin file with the remote and return the most recent assets.

    Returns a tuple of the most recent assets mapping it can get and a boolean denoting
    if the remote check happened or not. If it did then we have the most recent assets.
    """
    if not data_directory:
        if saved_assets is not None:
            # Do not read the all_assets file again if it has been already read
            return saved_assets, False

        # First initialization. Read the builtin all_assets.json
        root_dir = Path(__file__).resolve().parent.parent
        with open(root_dir / 'data' / 'all_assets.json', 'r') as f:
            assets = json.loads(f.read())

        return assets, False

    # else we got the data directory so we can finally do the remote check
    assets = _get_latest_assets(data_directory)
    return assets, True


class AssetResolver():
    __instance = None
    remote_check_happened: bool = False
    assets: Dict[str, Dict[str, Any]] = {}
    lowercase_mapping: Dict[str, str] = {}
    eth_token_info: Optional[List[EthTokenInfo]] = None

    def __new__(
            cls,
            data_directory: Path = None,
    ) -> 'AssetResolver':
        """Lazily initializes AssetResolver

        As long as it's called without a data_directory path it uses the builtin
        all_assets file. Once a data directory is given it attempts to see if a
        newer file exists on the remote and uses that. Once that's done the remote
        check flag is set to True.

        From that point on all calls to AssetResolver() return the same data.
        """
        if AssetResolver.__instance is not None:
            if AssetResolver.__instance.remote_check_happened:  # type: ignore
                return AssetResolver.__instance

            # else we still have not performed the remote check
            assets, check_happened = _attempt_initialization(
                data_directory=data_directory,
                saved_assets=AssetResolver.__instance.assets,
            )
        else:
            # first initialization
            assets, check_happened = _attempt_initialization(
                data_directory=data_directory,
                saved_assets=None,
            )
            AssetResolver.__instance = object.__new__(cls)

        AssetResolver.__instance.assets = assets
        # Mapping of lowercase identifier to file identifier to make sure our comparisons
        # are case insensitive. TODO: Eventually we can make this go away. We can achieve that by:
        # 1. Lowercasing all identifiers in the assets.json file
        # 2. Writing a DB upgrade to do the same everywhere in the DB where
        # an asset identifier is used for the user. That last part is doable but
        # a bit more tricky. See v13_v14 upgrade, plus consider all new tables
        # which have assets added to them.
        # 3. Everywhere in the code where we use identifiers such as mappings
        # we should now use the new lowercase identifiers. This is probably also
        # PITA.
        # ---> Think about it and if worth doing it address it
        AssetResolver.__instance.lowercase_mapping = {k.lower(): k for k, _ in assets.items()}
        AssetResolver.__instance.remote_check_happened = check_happened

        return AssetResolver.__instance

    @staticmethod
    def is_identifier_canonical(asset_identifier: str) -> Optional[str]:
        """Checks if an asset identifier exists and if yes returns its canonical form

        The canonical form is the one in the all_assets.json file and in the DB

        Also search for custom eth tokens if identifier starts with the ethereum
        directive. After the directive an ethereum address should follow
        """
        instance = AssetResolver()
        if asset_identifier.startswith(ETHEREUM_DIRECTIVE):
            token_data = _extract_custom_token_data(asset_identifier)
            return asset_identifier if token_data else None

        # else only other choice is all_assets.json
        return instance.lowercase_mapping.get(asset_identifier.lower(), None)

    @staticmethod
    def get_asset_data(asset_identifier: str) -> AssetData:
        """Get all asset data for a valid asset identifier

        Raises UnknownAsset if no data can be found
        """
        ended = None
        forked = None
        swapped_for = None

        if asset_identifier.startswith(ETHEREUM_DIRECTIVE):
            token_data = _extract_custom_token_data(asset_identifier)
            if token_data is None:
                raise UnknownAsset(asset_identifier)

            asset_type = AssetType.ETH_TOKEN
            ethereum_address = token_data.address
            if token_data.missing_basic_data():
                log.debug(
                    f'Considering ethereum token with address {ethereum_address}) '
                    f'as unknown since its missing either decimals or name or symbol',
                )
                raise UnknownAsset(asset_identifier)

            decimals = token_data.decimals
            name = token_data.name
            symbol = token_data.symbol
            started = token_data.started
            coingecko = token_data.coingecko
            cryptocompare = token_data.cryptocompare

        else:  # the most common case of an all assets entry
            data = AssetResolver().assets.get(asset_identifier, None)
            if data is None:
                raise UnknownAsset(asset_identifier)

            # If an unknown asset is found (can happen if list is updated but code is not)
            # then default to the "own chain" type"
            asset_type = asset_type_mapping.get(data['type'], AssetType.OWN_CHAIN)

            symbol = data['symbol']
            name = data['name']
            active = data.get('active', True)
            started = data.get('started', None)
            ended = data.get('ended', None)
            forked = data.get('forked', None)
            swapped_for = data.get('swapped_for', None)
            ethereum_address = data.get('ethereum_address', None)
            decimals = data.get('ethereum_token_decimals', None)
            cryptocompare = data.get('cryptocompare', None)
            coingecko = data.get('coingecko', None)

        return AssetData(
            identifier=asset_identifier,
            symbol=symbol,  # type: ignore  # checked with missing_basic_data
            name=name,  # type: ignore  # checked with missing_basic_data
            active=active,
            asset_type=asset_type,
            started=started,
            ended=ended,
            forked=forked,
            swapped_for=swapped_for,
            ethereum_address=ethereum_address,
            decimals=decimals,
            cryptocompare=cryptocompare,
            coingecko=coingecko,
        )

    @staticmethod
    def get_all_asset_data() -> Dict[str, Dict[str, Any]]:
        """Gets all the supported/known assets.

        Essentially the contents of all_assets.json and the custom ethereum
        tokens from the global DB
        """
        all_assets = AssetResolver().assets
        global_db_tokens = GlobalDBHandler().get_ethereum_tokens()
        all_assets.update({
            ETHEREUM_DIRECTIVE + x.address: x.serialize() for x in global_db_tokens
        })
        return all_assets

    @staticmethod
    def get_all_eth_token_info() -> List[EthTokenInfo]:
        """Gets all of the information about ethereum tokens we know

        Takes them out of all_assets.json and global token db
        """
        if AssetResolver().eth_token_info is not None:
            return AssetResolver().eth_token_info  # type: ignore
        all_tokens = []

        for identifier, asset_data in AssetResolver().assets.items():
            # If an unknown asset is found (can happen if list is updated but code is not)
            # then default to the "own chain" type"
            asset_type = asset_type_mapping.get(asset_data['type'], AssetType.OWN_CHAIN)
            if asset_type not in (AssetType.ETH_TOKEN_AND_MORE, AssetType.ETH_TOKEN):
                continue

            all_tokens.append(EthTokenInfo(
                identifier=identifier,
                address=ChecksumEthAddress(asset_data['ethereum_address']),
                symbol=asset_data['symbol'],
                name=asset_data['name'],
                decimals=int(asset_data['ethereum_token_decimals']),
            ))

        global_db_tokens = GlobalDBHandler().get_ethereum_tokens()
        for entry in global_db_tokens:
            if entry.missing_basic_data():
                continue

            all_tokens.append(EthTokenInfo(
                identifier=ETHEREUM_DIRECTIVE + entry.address,
                address=entry.address,
                symbol=entry.symbol,  # type: ignore  # checked with missing_basic_data
                name=entry.name,  # type: ignore  # checked with missing_basic_data
                decimals=entry.decimals,  # type: ignore  # checked with missing_basic_data
            ))

        AssetResolver().eth_token_info = all_tokens
        return all_tokens
