import csv
from collections import defaultdict
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, Iterator, List, TextIO, Tuple

import requests

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_COMBO,
    A_CORN,
    A_CRV,
    A_GRAIN,
    A_LDO,
    A_TORN,
    A_UNI,
)
from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

AIRDROPS = {
    'uniswap': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/d883cb7187a7c4fcf98c7a62f45568e7/raw/3718c95d572a29b9c3906d7c64726d3bd7524bfd/uniswap.csv',  # noqa: E501
        A_UNI,
        'https://app.uniswap.org/',
    ),
    '1inch': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/8f41d1511bf354d7e56810188116a410/raw/87d967e86e1435aa3a9ddb97ce20531e4e52dbad/1inch.csv',  # noqa: E501
        A_1INCH,
        'https://1inch.exchange/',
    ),
    'tornado': (
        # is checksummed
        'https://raw.githubusercontent.com/tornadocash/airdrop/master/airdrop.csv',
        A_TORN,  # Don't have TORN token yet?
        'https://tornado.cash/',
    ),
    'cornichon': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/5199d8bc6caa3253c343cd5084489088/raw/7e9ca4c4772fc50780bfe9997e1c43525e1b7445/cornichon_airdrop.csv',  # noqa: E501
        A_CORN,
        'https://cornichon.ape.tax/',
    ),
    'grain': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/08d7a5b28876741b300c944650c89280/raw/987ab4a92d5363fdbe262f639565732bd1fd3921/grain_iou.csv',  # noqa: E501
        A_GRAIN,
        'https://claim.harvest.finance/',
    ),
    'furucombo': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/69612e155e8063fd6b3422d4efbf22a3/raw/b9023960ab1c478ee2620c456e208e5124115c19/furucombo_airdrop.csv',  # noqa: E501
        A_COMBO,
        'https://furucombo.app/',
    ),
    'lido': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/57a8d65280a482fed6f3e2cc00c0e540/raw/e6ebac56c438cc8a882585c5f5bfba64eb57c424/lido_airdrop.csv',  # noqa: E501
        A_LDO,
        'https://lido.fi/',
    ),
    'curve': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/b712df84fe549b3e886a8ee5ce1da27b/raw/4454cadaffc876839775ddc8bafdb044e797b04f/curve_airdrop.csv',  # noqa: E501
        A_CRV,
        'https://www.curve.fi/',
    ),
}

POAP_AIRDROPS = {
    'aave_v2_pioneers': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/698c6c0685643802a5da9689aa1c4919/raw/a8c5bfb91c8328f8a9d2b6f853a0a55328458ed7/poap_aave_v2_pioneers.json',  # noqa: E501
        'https://poap.delivery/aave-v2-pioneers',
        'AAVE V2 Pioneers',
    ),
    'beacon_chain_first_1024': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/3dccfb765d7294370811bdf4f6b539f6/raw/2ee02c22b68b90333359e2f1d24ff5d460dba092/poap_beacon_chain_first_1024.json',  # noqa: E501
        'https://poap.delivery/beacon-chain-first-1024',
        'Beacon Chain First 32,769 Block Validators',
    ),
    'beacon_chain_first_32769': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/1bbd649ee970a417ef13d847b3fe6c60/raw/1e2e6ebc8c29ba75c2189a5780c132da4ed8530c/poap_beacon_chain_first_32769.json',  # noqa: E501
        'https://poap.delivery/beacon-chain-first-32769',
        'Beacon Chain First 1024 Depositors and Proposers',
    ),
    'coingecko_yield_farming': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/293e2ebc3070fe49d93d4ed04daf6588/raw/25ee4153498e9a4c709542d6f541cc9ab76997d8/poap_coingecko_yield_farming.json',  # noqa: E501
        'https://poap.delivery/coin-gecko',
        'Coin Gecko Yield Farming',
    ),
    'eth2_genesis': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/047e8dfbadf5459cc70fe19c4e2e6672/raw/e55baebe6657c11c73b6b808cb269fab31c02da8/poap_eth2_genesis.json',  # noqa: E501
        'https://poap.delivery/eth2-genesis/',
        'Beacon Chain Genesis Depositor',
    ),
    'half_rekt': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/cd1d137d871faf02877287c9dac51a46/raw/a0a09372d5bf01285490108661a7c223c1a7de8d/poap_half_rekt.json',  # noqa: E501
        'https://poap.delivery/half-rekt',
        'Half Rekt',
    ),
    'keep_stakers': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/09ac96c513852268eda698130bcacd20/raw/69ed0700a9f7432d783148c89872b86f1d0ee3dd/poap_keep_stakers.json',  # noqa: E501
        'https://poap.delivery/keep-stakers',
        'KEEP Network Mainnet Stakers',
    ),
    'lumberjackers': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/f1c947259488e0165367c015af93c933/raw/a456fcd1eb1ddedac1cf4b6dd4bbb2d57371f028/poap_lumberjackers.json',  # noqa: E501
        'https://poap.delivery/lumberjackers',
        'False Start Lumberjackers',
    ),
    'medalla': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/17cc2deb28ec15912eca8ec4ccad9feb/raw/196ccb50451d908d71cca4bc43731d6547b2276b/poap_medalla.json',  # noqa: E501
        'https://poap.delivery/medalla',
        'Medalla Validator',
    ),
    'muir_glacier': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/1508221a0d9c832a046782f8c8c2c58c/raw/d339cfd94885874cb83d829e815212cd29cbb66f/poap_muir_glacier.json',  # noqa: E501
        'https://poap.delivery/muir-glacier',
        'Muir Glacier',
    ),
    'proof_of_gucci': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/aeeda0c9f8f07b00c3b5e15c200808b0/raw/e5adb753a3a86f0a50bf93137e2c4adc61548293/poap_proof_of_gucci.json',  # noqa: E501
        'https://poap.delivery/proof-of-gucci',
        'YFI - Proof of Gucci',
    ),
    'proof_of_gucci_design_competition': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/76bdee77f74b12bdb9f9167e06c32047/raw/a0851ce92ca2f668e17a97c9df982bc3e12f9bb3/poap_proof_of_gucci_design_competition.json',  # noqa: E501
        'https://poap.delivery/proof-of-gucci-design',
        'YFI - Proof of Gucci Design Competition',
    ),
    'resucitators': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/badab170c4ffe732bf13b73546f521b0/raw/f003083090efd834bcee1d0d1fe4e218380aa0cf/poap_resucitators.json',  # noqa: E501
        'https://poap.delivery/medalla-resuscitator',
        'Medalla Resuscitators',
    ),
    'yam': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/a86dae3d8d03c2fd676fbf2d5f7b2709/raw/fa0a603117f6e3e807a49491924aaaa2bc89179a/poap_yam.json',  # noqa: E501
        'https://poap.delivery/yam',
        'Yam Heroes',
    ),
    'ycover': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/87a8f834463f7dd165cad9bcd0df8dec/raw/59ff367bd532f632ce94e69900709155a55de82a/poap_ycover.json',  # noqa: E501
        'https://poap.delivery/ycover',
        'A New Face For yCover',
    ),
    'yfi_og': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/ecf5327338b684495a44fbd28a0dbb14/raw/3292995f530baedcdacde02526c6b2bd1de0e110/poap_yfi_og.json',  # noqa: E501
        'https://poap.delivery/yfi-og',
        'I Played 4 YFI',
    ),
}


def get_airdrop_data(name: str, data_dir: Path) -> Tuple[Iterator, TextIO]:
    airdrops_dir = data_dir / 'airdrops'
    airdrops_dir.mkdir(parents=True, exist_ok=True)
    filename = airdrops_dir / f'{name}.csv'
    if not filename.is_file():
        # if not cached, get it from the gist
        try:
            request = requests.get(AIRDROPS[name][0])
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Airdrops Gist request failed due to {str(e)}') from e

        with open(filename, 'w') as f:
            f.write(request.content.decode('utf-8'))

    csvfile = open(filename, 'r')
    iterator = csv.reader(csvfile)
    next(iterator)  # skip header
    return iterator, csvfile


def get_poap_airdrop_data(name: str, data_dir: Path) -> Dict[str, Any]:
    airdrops_dir = data_dir / 'airdrops_poap'
    airdrops_dir.mkdir(parents=True, exist_ok=True)
    filename = airdrops_dir / f'{name}.json'
    if not filename.is_file():
        # if not cached, get it from the gist
        try:
            request = requests.get(POAP_AIRDROPS[name][0])
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'POAP airdrops Gist request failed due to {str(e)}') from e

        try:
            json_data = rlk_jsonloads_dict(request.content.decode('utf-8'))
        except JSONDecodeError as e:
            raise RemoteError(f'POAP airdrops Gist contains an invalid JSON {str(e)}') from e

        with open(filename, 'w') as outfile:
            outfile.write(rlk_jsondumps(json_data))

    infile = open(filename, 'r')
    data_dict = rlk_jsonloads_dict(infile.read())
    return data_dict


def check_airdrops(
        addresses: List[ChecksumEthAddress],
        data_dir: Path,
) -> Dict[ChecksumEthAddress, Dict]:
    """Checks airdrop data for the given list of ethereum addresses

    May raise:
        - RemoteError if the remote request fails
    """
    found_data: Dict[ChecksumEthAddress, Dict] = defaultdict(lambda: defaultdict(dict))
    for protocol_name, airdrop_data in AIRDROPS.items():
        data, csvfile = get_airdrop_data(protocol_name, data_dir)
        for addr, amount, *_ in data:
            # not doing to_checksum_address() here since the file addresses are checksummed
            # and doing to_checksum_address() so many times hits performance
            if protocol_name in ('cornichon', 'tornado', 'grain', 'lido'):
                amount = token_normalized_value_decimals(int(amount), 18)
            if addr in addresses:
                found_data[addr][protocol_name] = {
                    'amount': str(amount),
                    'asset': airdrop_data[1],
                    'link': airdrop_data[2],
                }
        csvfile.close()

    # TODO: fix next line annotation
    for protocol_name, airdrop_data in POAP_AIRDROPS.items():  # type: ignore
        data_dict = get_poap_airdrop_data(protocol_name, data_dir)
        for addr, assets in data_dict.items():
            # not doing to_checksum_address() here since the file addresses are checksummed
            # and doing to_checksum_address() so many times hits performance
            if addr in addresses:
                if 'poap' not in found_data[addr]:
                    found_data[addr]['poap'] = []

                found_data[addr]['poap'].append({
                    'event': protocol_name,
                    'assets': assets,
                    'link': airdrop_data[1],
                    'name': airdrop_data[2],
                })

    return dict(found_data)
