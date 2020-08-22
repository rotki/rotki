import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import AssetData, AssetType, ChecksumEthAddress, EthTokenInfo

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
}


def _get_latest_assets(data_directory: Path) -> Dict[str, Any]:
    """Gets the latest assets either locally or from the remote

    Checks the remote (github) and if there is a newer file there it pulls it,
    saves it and its md5 hash locally and returns the new assets.

    If there is no new file (same hash) or if there is any problem contacting the remote
    then the builtin assets file is used.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    our_downloaded_md5 = data_directory / 'assets' / 'all_assets.md5'
    our_builtin_md5 = root_dir / 'data' / 'all_assets.md5'
    try:
        response = requests.get('https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.md5')  # noqa: E501
        remote_md5 = response.text
        if our_downloaded_md5.is_file():
            local_md5_file = our_downloaded_md5
        else:
            local_md5_file = our_builtin_md5

        with open(local_md5_file, 'r') as f:
            local_md5 = f.read()

        if local_md5 != remote_md5:
            # we need to download and save the new assets from github
            response = requests.get('https://raw.githubusercontent.com/rotki/rotki/develop/rotkehlchen/data/all_assets.json')  # noqa: E501
            remote_asset_data = response.text

            with open(data_directory / 'assets' / 'all_assets.md5', 'w') as f:
                f.write(remote_md5)
            with open(data_directory / 'assets' / 'all_assets.json', 'w') as f:
                f.write(remote_asset_data)

            log.info(
                f'Found newer remote assets file with {remote_md5} md5 hash. Replaced local file',
            )
            return json.loads(remote_asset_data)

        # else, same as RemotError use the current one
    except RemoteError:
        pass

    if our_downloaded_md5.is_file():
        assets_file = data_directory / 'assets' / 'all_assets.json'
    else:
        assets_file = root_dir / 'data' / 'all_assets.json'

    with open(assets_file, 'r') as f:
        return json.loads(f.read())


class AssetResolver():
    __instance = None
    assets: Dict[str, Dict[str, Any]] = {}
    eth_token_info: Optional[List[EthTokenInfo]] = None

    def __new__(
            cls,
            data_directory: Path = None,
    ) -> 'AssetResolver':
        if AssetResolver.__instance is not None:
            return AssetResolver.__instance  # type: ignore

        assert data_directory, 'arguments should be given at the first instantiation'

        AssetResolver.__instance = object.__new__(cls)
        assets = _get_latest_assets(data_directory)
        root_dir = Path(__file__).resolve().parent.parent.parent
        with open(root_dir / 'data' / 'all_assets.json', 'r') as f:
            assets = json.loads(f.read())

        AssetResolver.__instance.assets = assets
        return AssetResolver.__instance

    @staticmethod
    def is_identifier_canonical(asset_identifier: str) -> bool:
        """Checks if an asset identifier is canonical"""
        return asset_identifier in AssetResolver().assets

    @staticmethod
    def get_asset_data(asset_identifier: str) -> AssetData:
        """Get all asset data from the known assets file for valid asset symbol"""
        data = AssetResolver().assets[asset_identifier]
        asset_type = asset_type_mapping[data['type']]
        result = AssetData(
            identifier=asset_identifier,
            symbol=data['symbol'],
            name=data['name'],
            # If active is in the data use it, else we assume it's true
            active=data.get('active', True),
            asset_type=asset_type,
            started=data.get('started', None),
            ended=data.get('ended', None),
            forked=data.get('forked', None),
            swapped_for=data.get('swapped_for', None),
            ethereum_address=data.get('ethereum_address', None),
            decimals=data.get('ethereum_token_decimals', None),
            cryptocompare=data.get('cryptocompare', None),
            coingecko=data.get('coingecko', None),
        )
        return result

    @staticmethod
    def get_all_eth_token_info() -> List[EthTokenInfo]:
        if AssetResolver().eth_token_info is not None:
            return AssetResolver().eth_token_info  # type: ignore
        all_tokens = []

        for identifier, asset_data in AssetResolver().assets.items():
            asset_type = asset_type_mapping[asset_data['type']]
            if asset_type not in (AssetType.ETH_TOKEN_AND_MORE, AssetType.ETH_TOKEN):
                continue

            all_tokens.append(EthTokenInfo(
                identifier=identifier,
                address=ChecksumEthAddress(asset_data['ethereum_address']),
                symbol=asset_data['symbol'],
                name=asset_data['name'],
                decimals=int(asset_data['ethereum_token_decimals']),
            ))

        AssetResolver().eth_token_info = all_tokens
        return all_tokens
