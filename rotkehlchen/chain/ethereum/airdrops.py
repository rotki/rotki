import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, TextIO, Tuple

import requests

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.constants.assets import A_1INCH, A_COMBO, A_CORN, A_GRAIN, A_LDO, A_TORN, A_UNI
from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import ChecksumEthAddress

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
        'https://gist.githubusercontent.com/vnavascues/5f32d53a7ebd1ea844f10cb48e7b7002/raw/fa0c947c6dd1ee2a7b16674a86f0e50cb7bbe631/furucombo_airdrop.csv',  # noqa: E501
        A_COMBO,
        'https://furucombo.app/',
    ),
    'lido': (
        # is checksummed
        'https://gist.githubusercontent.com/vnavascues/6fea5eb631af7e0b8a910e8c62cd471e/raw/fa529e9cc5a90e0970f59f69c649e45b2008bbf9/lido_airdrop.csv',  # noqa: E501
        A_LDO,
        'https://lido.fi/',
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

    return dict(found_data)
