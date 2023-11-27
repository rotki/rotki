import csv
import logging
from collections import defaultdict
from collections.abc import Iterator, Sequence
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Any, NamedTuple

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_COMBO,
    A_CORN,
    A_CRV,
    A_CVX,
    A_DIVA,
    A_ENS,
    A_FOX,
    A_GNOSIS_VCOW,
    A_GRAIN,
    A_LDO,
    A_PSP,
    A_SDL,
    A_TORN,
    A_UNI,
    A_VCOW,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, FValWithTolerance
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SMALLEST_AIRDROP_SIZE = 20900


class Airdrop(NamedTuple):
    """Airdrop class for representing airdrop data.

    This contains the definition of the Airdrop class, which is used to represent
    individual airdrops along with their associated data, such as URL, token address,
    website URL, name, and icon filename.
    """
    csv_url: str
    asset: Asset
    url: str
    name: str
    icon: str


AIRDROPS: dict[str, Airdrop] = {
    'uniswap': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/d883cb7187a7c4fcf98c7a62f45568e7/raw/3718c95d572a29b9c3906d7c64726d3bd7524bfd/uniswap.csv',
        asset=A_UNI,
        url='https://app.uniswap.org/',
        name='Uniswap',
        icon='uniswap.svg',
    ),
    '1inch': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/8f41d1511bf354d7e56810188116a410/raw/87d967e86e1435aa3a9ddb97ce20531e4e52dbad/1inch.csv',
        asset=A_1INCH,
        url='https://1inch.exchange/',
        name='1inch',
        icon='1inch.svg',
    ),
    'tornado': Airdrop(
        # is checksummed
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/tornado.csv',
        asset=A_TORN,
        url='https://tornado.cash/',
        name='Tornado Cash',
        icon='tornado.svg',
    ),
    'cornichon': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/5199d8bc6caa3253c343cd5084489088/raw/7e9ca4c4772fc50780bfe9997e1c43525e1b7445/cornichon_airdrop.csv',
        asset=A_CORN,
        url='https://cornichon.ape.tax/',
        name='Cornichon',
        icon='cornichon.svg',
    ),
    'grain': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/08d7a5b28876741b300c944650c89280/raw/987ab4a92d5363fdbe262f639565732bd1fd3921/grain_iou.csv',
        asset=A_GRAIN,
        url='https://claim.harvest.finance/',
        name='Grain',
        icon='grain.png',
    ),
    'furucombo': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/69612e155e8063fd6b3422d4efbf22a3/raw/b9023960ab1c478ee2620c456e208e5124115c19/furucombo_airdrop.csv',
        asset=A_COMBO,
        url='https://furucombo.app/',
        name='Furucombo',
        icon='furucombo.svg',
    ),
    'lido': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/57a8d65280a482fed6f3e2cc00c0e540/raw/e6ebac56c438cc8a882585c5f5bfba64eb57c424/lido_airdrop.csv',
        asset=A_LDO,
        url='https://lido.fi/',
        name='Lido',
        icon='lido.svg',
    ),
    'curve': Airdrop(
        # is checksummed
        csv_url='https://gist.githubusercontent.com/LefterisJP/9a37e5342ddb6219a805a82bcd3d63fe/raw/71e89f0e95ea8ef5503fb1ac569447fea63f1ede/curve_airdrop.csv',
        asset=A_CRV,
        url='https://www.curve.fi/',
        name='Curve Finance',
        icon='curve.png',
    ),
    'convex': Airdrop(
        csv_url='https://gist.githubusercontent.com/LefterisJP/fd0ebccbc645f7de2b142907bd207363/raw/0613689dd5212b81788ed1a108c751b29b2ce93a/convex_airdrop.csv',
        asset=A_CVX,
        url='https://www.convexfinance.com/',
        name='Convex',
        icon='convex.jpeg',
    ),
    'shapeshift': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/shapeshift.csv',
        asset=A_FOX,
        url='https://shapeshift.com/shapeshift-decentralize-airdrop',
        name='ShapeShift',
        icon='shapeshift.svg',
    ),
    'ens': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/ens.csv',
        asset=A_ENS,
        url='https://claim.ens.domains/',
        name='ENS',
        icon='ens.svg',
    ),
    'psp': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/psp.csv',
        asset=A_PSP,
        url='https://paraswap.io/',
        name='ParaSwap',
        icon='paraswap.svg',
    ),
    'sdl': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/saddle_finance.csv',
        asset=A_SDL,
        url='https://saddle.exchange/#/',
        name='SaddleFinance',
        icon='saddle-finance.svg',
    ),
    'cow_mainnet': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/cow_mainnet.csv',
        asset=A_VCOW,
        url='https://cowswap.exchange/#/claim',
        name='COW (ethereum)',
        icon='cow.svg',
    ),
    'cow_gnosis': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/main/airdrops/cow_gnosis.csv',
        asset=A_GNOSIS_VCOW,
        url='https://cowswap.exchange/#/claim',
        name='COW (gnosis chain)',
        icon='cow.svg',
    ),
    'diva': Airdrop(
        csv_url='https://raw.githubusercontent.com/rotki/data/develop/airdrops/diva.csv',
        asset=A_DIVA,
        url='https://claim.diva.community/',
        name='DIVA',
        icon='diva.svg',
    ),
}

POAP_AIRDROPS = {
    'aave_v2_pioneers': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/569992ba1536474f97f7c74104e66354/raw/a8c5bfb91c8328f8a9d2b6f853a0a55328458ed7/poap_aave_v2_pioneers.json',
        'https://poap.delivery/aave-v2-pioneers',
        'AAVE V2 Pioneers',
    ),
    'beacon_chain_first_1024': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/73469098efe0b12965e5752899be00fe/raw/2ee02c22b68b90333359e2f1d24ff5d460dba092/poap_beacon_chain_first_1024.json',
        'https://poap.delivery/beacon-chain-first-1024',
        'Beacon Chain First 1024 Depositors and Proposers',
    ),
    'beacon_chain_first_32769': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/6302f4e6da6c1488427fbb8b6207222e/raw/1e2e6ebc8c29ba75c2189a5780c132da4ed8530c/poap_beacon_chain_first_32769.json',
        'https://poap.delivery/beacon-chain-first-32769',
        'Beacon Chain First 32,769 Block Validators',
    ),
    'coingecko_yield_farming': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/58d23332afc6e9fe701ecc80fcc864f6/raw/25ee4153498e9a4c709542d6f541cc9ab76997d8/poap_coingecko_yield_farming.json',
        'https://poap.delivery/coin-gecko',
        'Coin Gecko Yield Farming',
    ),
    'eth2_genesis': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/7ce2c343de427c9fe6f54dc9bd6d1a0c/raw/e55baebe6657c11c73b6b808cb269fab31c02da8/poap_eth2_genesis.json',
        'https://poap.delivery/eth2-genesis/',
        'Beacon Chain Genesis Depositor',
    ),
    'half_rekt': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/429e9c9b3948499cfe793cea75a3b0d6/raw/a0a09372d5bf01285490108661a7c223c1a7de8d/poap_half_rekt.json',
        'https://poap.delivery/half-rekt',
        'Half Rekt',
    ),
    'keep_stakers': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/b794526fb996cb85dfb825ee5f814e4f/raw/69ed0700a9f7432d783148c89872b86f1d0ee3dd/poap_keep_stakers.json',
        'https://poap.delivery/keep-stakers',
        'KEEP Network Mainnet Stakers',
    ),
    'lumberjackers': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/802359b6825472ee0081580dbe1a1c82/raw/a456fcd1eb1ddedac1cf4b6dd4bbb2d57371f028/poap_lumberjackers.json',
        'https://poap.delivery/lumberjackers',
        'False Start Lumberjackers',
    ),
    'medalla': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/1a293bf46b388f709df84ff98c5c5cc6/raw/196ccb50451d908d71cca4bc43731d6547b2276b/poap_medalla.json',
        'https://poap.delivery/medalla',
        'Medalla Validator',
    ),
    'muir_glacier': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/d135745cf9f4f3143555e0f6a8f0d804/raw/d34c93087100168cac0dfd0ab46254b4a82ff0b8/poap_muir_glacier.json',
        'https://poap.delivery/muir-glacier',
        'Muir Glacier',
    ),
    'proof_of_gucci': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/43b2c4bb73923d7bb3eaf3b329f7f7a1/raw/e5adb753a3a86f0a50bf93137e2c4adc61548293/poap_proof_of_gucci.json',
        'https://poap.delivery/proof-of-gucci',
        'YFI - Proof of Gucci',
    ),
    'proof_of_gucci_design_competition': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/40c6b2a94d4b8d7f442522b099e5e258/raw/a0851ce92ca2f668e17a97c9df982bc3e12f9bb3/poap_proof_of_gucci_design_competition.json',
        'https://poap.delivery/proof-of-gucci-design',
        'YFI - Proof of Gucci Design Competition',
    ),
    'resuscitators': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/0ac0216f82f16453b74a40529384a152/raw/f003083090efd834bcee1d0d1fe4e218380aa0cf/poap_resucitators.json',
        'https://poap.delivery/medalla-resuscitator',
        'Medalla Resuscitators',
    ),
    'yam': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/d676e1f3db8df96928c2501c6be434ac/raw/fa0a603117f6e3e807a49491924aaaa2bc89179a/poap_yam.json',
        'https://poap.delivery/yam',
        'Yam Heroes',
    ),
    'ycover': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/727c05f3a9cab79059258528595c102e/raw/59ff367bd532f632ce94e69900709155a55de82a/poap_ycover.json',
        'https://poap.delivery/ycover',
        'A New Face For yCover',
    ),
    'yfi_og': (
        # is checksummed
        'https://gist.githubusercontent.com/LefterisJP/58862ec2b398c770d60c24e50e18e50c/raw/3292995f530baedcdacde02526c6b2bd1de0e110/poap_yfi_og.json',
        'https://poap.delivery/yfi-og',
        'I Played 4 YFI',
    ),
}


def get_airdrop_data(name: str, data_dir: Path) -> Iterator[list[str]]:
    airdrops_dir = data_dir / 'airdrops'
    airdrops_dir.mkdir(parents=True, exist_ok=True)
    filename = airdrops_dir / f'{name}.csv'
    if not filename.is_file():
        # if not cached, get it from the gist
        try:
            response = requests.get(url=AIRDROPS[name][0], timeout=(30, 100))  # a large read timeout is necessary because the queried data is quite large  # noqa: E501
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Airdrops Gist request failed due to {e!s}') from e
        try:
            content = response.text
            if (
                not csv.Sniffer().has_header(content) or
                len(response.content) < SMALLEST_AIRDROP_SIZE
            ):
                raise csv.Error
            with open(filename, 'w', encoding='utf8') as f:
                f.write(content)
        except csv.Error as e:
            log.debug(f'airdrop file {filename} contains invalid data {content}')
            raise UnableToDecryptRemoteData(
                f'File {filename} contains invalid data. Check logs.',
            ) from e
    # Verify the CSV file
    with open(filename, encoding='utf8') as csvfile:
        iterator = csv.reader(csvfile)
        next(iterator)  # skip header
        yield from iterator


def get_poap_airdrop_data(name: str, data_dir: Path) -> dict[str, Any]:
    airdrops_dir = data_dir / 'airdrops_poap'
    airdrops_dir.mkdir(parents=True, exist_ok=True)
    filename = airdrops_dir / f'{name}.json'
    if not filename.is_file():
        # if not cached, get it from the gist
        try:
            request = requests.get(url=POAP_AIRDROPS[name][0], timeout=CachedSettings().get_timeout_tuple())  # noqa: E501
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'POAP airdrops Gist request failed due to {e!s}') from e

        try:
            json_data = jsonloads_dict(request.content.decode('utf-8'))
        except JSONDecodeError as e:
            raise RemoteError(f'POAP airdrops Gist contains an invalid JSON {e!s}') from e

        with open(filename, 'w', encoding='utf8') as outfile:
            outfile.write(rlk_jsondumps(json_data))

    with open(filename, encoding='utf8') as infile:
        data_dict = jsonloads_dict(infile.read())
    return data_dict


def calculate_claimed_airdrops(
        airdrop_data: list[tuple[ChecksumEvmAddress, Asset, FValWithTolerance]],
        database: DBHandler,
) -> list[tuple[ChecksumEvmAddress, Asset, FVal]]:
    """Calculates which of the given airdrops have been claimed.
    It does so by checking if there is a claim history event in the database
    that matches the airdrop data (address, asset and amount). It returns a list
    of tuples with the airdrop data for which a claim event was found."""
    if len(airdrop_data) == 0:
        return []

    query_parts = []
    bindings = [HistoryEventType.RECEIVE.serialize(), HistoryEventSubType.AIRDROP.serialize()]
    for airdrop_info in airdrop_data:
        amount_with_tolerance = airdrop_info[2]
        amount = amount_with_tolerance.value
        half_range = amount_with_tolerance.tolerance / 2
        query_parts.append('events.location_label=? AND events.asset=? AND CAST(events.amount AS REAL) BETWEEN ? AND ?')  # noqa: E501
        bindings.extend([airdrop_info[0], airdrop_info[1].serialize(), str(amount - half_range), str(amount + half_range)])  # noqa: E501

    query_part = ' OR '.join(query_parts)
    with database.conn.read_ctx() as cursor:
        claim_events = cursor.execute(
            'SELECT events.location_label, events.asset, events.amount '
            'FROM history_events AS events '
            'WHERE events.type=? AND events.subtype=? '
            f'AND {query_part}',
            tuple(bindings),
        ).fetchall()

    return [(event[0], event[1], event[2]) for event in claim_events]


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
    data_dir = database.user_data_dir.parent
    airdrop_tuples = []
    for protocol_name, airdrop_data in AIRDROPS.items():
        for row in get_airdrop_data(protocol_name, data_dir):
            if len(row) < 2:
                raise UnableToDecryptRemoteData(
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
                asset = airdrop_data[1]
                found_data[addr][protocol_name] = {  # type: ignore
                    'amount': str(amount),
                    'asset': asset,
                    'link': airdrop_data[2],
                    'claimed': False,
                }
                airdrop_tuples.append((
                    string_to_evm_address(addr),
                    asset,
                    FValWithTolerance(
                        value=FVal(amount),
                        tolerance=tolerance_for_amount_check,
                    ),
                ))

    asset_to_protocol = {item[1]: protocol for protocol, item in AIRDROPS.items()}
    claim_events_tuple = calculate_claimed_airdrops(
        airdrop_data=airdrop_tuples,
        database=database,
    )
    for event_tuple in claim_events_tuple:
        found_data[event_tuple[0]][asset_to_protocol[event_tuple[1]]]['claimed'] = True

    for protocol_name, poap_airdrop_data in POAP_AIRDROPS.items():
        data_dict = get_poap_airdrop_data(protocol_name, data_dir)
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
