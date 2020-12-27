from rotkehlchen.typing import ChecksumEthAddress
from typing import List, Dict, TextIO, Iterator, Tuple
from rotkehlchen.constants.assets import A_UNI, A_1INCH
import csv
import requests
from pathlib import Path
from collections import defaultdict
from rotkehlchen.errors import RemoteError

AIRDROPS = {
    "uniswap": (
        # is checksummed
        "https://raw.githubusercontent.com/banteg/uniswap-distribution/master/uniswap-distribution.csv",  # noqa: E501
        A_UNI,
    ),
    "1inch": (
        # is checksummed
        "https://gist.githubusercontent.com/banteg/12708815fb63239d9f28dec5df8641f9/raw/28a9dffe9d5681ef5f75b0ab6c39fe5ea0064712/1inch.csv",  # noqa: E501
        A_1INCH,
    ),
    "tornado": (
        # is checksummed
        "https://raw.githubusercontent.com/tornadocash/airdrop/master/airdrop.csv",
        A_UNI,  # Don't have TORN token yet?
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
            if addr in addresses:
                found_data[addr][protocol_name] = {
                    'amount': amount,
                    'asset': airdrop_data[1],
                }
        csvfile.close()

    return dict(found_data)
