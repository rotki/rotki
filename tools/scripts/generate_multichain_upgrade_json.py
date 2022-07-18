"""Script to create a json file with mapping of asset identifiers to addresses of the assets in
various platforms.

If the asset has other platforms known to coingecko is a mapping of addreses like below:
{
    "ethereum": "0x6b175474e89094c44da98b954eedeac495271d0f",
    "polygon-pos": "0x8f3cf7ad23cd3cadbd9735aff958023239c6a063",
    "binance-smart-chain": "0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3",
    "optimistic-ethereum": "0xda10009cbd5d07dd0cecc66161fc93d7c9000da1",
}

If not it's a mapping to an empty string to signify the asset has been queried

Run the script as many times as is needed to complete the entire json file

Once it's run you can also give the --clean argument which will take the file and clean it from
all empty string value assets, so the end result contains only identifiers that exists in other
platforms
"""

from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.coingecko import DELISTED_ASSETS, Coingecko
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.logging import TRACE, add_logging_level


class ScriptGecko(Coingecko):

    def get_coin_data(self, coin_id: str) -> Optional[Dict[str, str]]:
        options = {
            # Include all localized languages in response (true/false) [default: true]
            'localization': 'false',
            # Include tickers data (true/false) [default: true]
            'tickers': 'false',
            # Include market_data (true/false) [default: true]
            'market_data': 'false',
            # Include communitydata (true/false) [default: true]
            'community_data': 'false',
            # Include developer data (true/false) [default: true]
            'developer_data': 'false',
            # Include sparkline 7 days data (eg. true, false) [default: false]
            'sparkline': 'false',
        }
        data = self._query(
            module='coins',
            subpath=f'{coin_id}',
            options=options,
        )
        return data.get('platforms', None)


def _query_and_populate(coingecko: Coingecko, json_data: Dict[str, Any]) -> Dict[str, Any]:
    globaldb = GlobalDBHandler()
    assets = globaldb.get_all_asset_data(mapping=False)
    for entry in assets:
        if entry.identifier in json_data:
            continue  # already processed

        if entry.identifier in DELISTED_ASSETS:
            print(f'Asset {entry.identifier} {entry.symbol} is delisted from coingecko. Skipping')
            json_data[entry.identifier] = ''  # just to know it has been queried
            continue

        if entry.coingecko is None or entry.coingecko == '':
            print(f'Asset {entry.identifier} {entry.symbol} has no coingecko id. Skipping')
            json_data[entry.identifier] = ''  # just to know it has been queried
            continue

        try:
            protocols = coingecko.get_coin_data(entry.coingecko)
        except RemoteError as e:
            error_msg = str(e)
            if 'HTTP status code: 404' in error_msg:
                print(f'Asset {entry.identifier} {entry.symbol} cant be found in the coins endpoint')  # noqa: E501
                json_data[entry.identifier] = ''  # just to know it has been queried
                continue  # cant find the token in this endpoint. Unfortunately coingecko does that
            print(f'Error while querying coingecko: {str(e)} for {entry.identifier}')
            break  # break out of the loop and write json data we got so far

        json_data[entry.identifier] = '' if protocols is None else protocols
    else:
        print('Success! iterated all assets')

    return json_data


def _clean(json_data: Dict[str, Any]) -> Dict[str, Any]:
    new_data = json_data.copy()
    for identifier, value in json_data.items():
        if value == '':
            new_data.pop(identifier)

    return new_data


def main():
    add_logging_level('TRACE', TRACE)
    parser = argparse.ArgumentParser(description='Get multichain information')  # noqa: E501
    parser.add_argument('-o', '--output', type=str, help='Output json file. If existing its appended to')  # noqa: E501
    parser.add_argument('-c', '--clean', action='store_true', help='Clean file from all empty value assets')  # noqa: E501
    args = parser.parse_args()
    coingecko = ScriptGecko()
    data_dir = Path('/home/lefteris/.local/share/rotki/data')
    GlobalDBHandler(data_dir=data_dir)

    output_path = Path(args.output)
    json_data = {}
    if output_path.is_file():
        with open(output_path, 'r') as f:
            json_data = json.load(f)

    if args.clean:
        json_data = _clean(json_data)
    else:
        json_data = _query_and_populate(coingecko, json_data)

    with open(output_path, 'w') as f:
        f.write(json.dumps(json_data))


if __name__ == "__main__":
    main()
