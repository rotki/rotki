import sys
from typing import Any, Dict

from asset_aggregator.utils import choose_multiple

from rotkehlchen.constants import FIAT_CURRENCIES
from rotkehlchen.utils import createTimeStamp, iso8601ts_to_timestamp

# For these assets we will definitely always use our data as they are more accurate
PREFER_OUR_STARTED = (
    # BCH forked on https://www.blockchain.com/btc/block-height/478558
    # and our data contain the correct timestamp
    'BCH',
    # The first BTC block timestamp is wrong in coin paprika. Our data is accurate
    # Taken from https://www.blockchain.com/btc/block-height/0
    'BTC',
    # The first DASH block is wrong in coin paprika. Our data is accurate.
    # Taken from:
    # https://explorer.dash.org/block/00000ffd590b1485b3caadc19b22e6379c733355108f107a430458cdf3407ab6
    'DASH',
    # The first DOGE block is wrong in coin paprika. Our data is accurate.
    # Taken from: https://dogechain.info/block/0
    'DOGE',
    # ETC forked on https://etherscan.io/block/1920000 and our data contain the
    # correct timestamp
    'ETC',
    # https://www.cryptoninjas.net/2017/04/24/gnosis-token-sale-ends-312-8-million-raised-hour/
    # Gno token sale ended on 24/04/2017 not on 2015 ..
    'GNO',
    # LTC first block was mined https://blockchair.com/litecoin/block/0
    # our data is more accurate
    'LTC',
    # Namecoin's first block was mined https://namecha.in/block/0
    # our data is more accurate
    'NMC',
    # VET is a cotinuation of VEN and coinpaprika regards VET's started as VEN's
    # started which is not what we need
    'VET',
    # Coin paprika's stellar XLM date is one year earlier than the actual launch
    # .. no idea why
    'XLM',
    # Monero's first block is mined https://moneroblocks.info/block/1
    # Our data is more accurate
    'XMR',
    # ZEC's first block is mined https://explorer.zcha.in/blocks/1
    # Our data is more accurate
    'ZEC',
)


def timerange_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Process the started timestamps from coin paprika and coinmarketcap.

    Then compare to our data and provide choices to clean up the data.
    """
    if asset_symbol in FIAT_CURRENCIES:
        # Fiat does not have started date (or we don't care about it)
        return our_data

    paprika_started = paprika_data['started_at']
    cmc_started = None
    if cmc_data:
        cmc_started = cmc_data['first_historical_data']

    if not cmc_started and not paprika_started:
        print(f'Did not find a started date for asset {asset_symbol} in any of the external APIs')
        return our_data

    paprika_started_ts = createTimeStamp(paprika_started, formatstr='%Y-%m-%dT%H:%M:%SZ')
    cmc_started_ts = None
    if cmc_data:
        cmc_started_ts = iso8601ts_to_timestamp(cmc_started)

    if asset_symbol in PREFER_OUR_STARTED:
        # Already manually checked
        return our_data

    our_started = our_asset.get('started', None)
    if our_started != cmc_started or our_started != paprika_started:
        msg = (
            f'For asset {asset_symbol} the started times are: \n'
            f'(1) Our data: {our_started}\n'
            f'(2) Coinpaprika: {paprika_started_ts}\n'
            f'(3) Coinmarketcap: {cmc_started_ts}\n'
            f'Choose a number (1)-(3) to choose which timestamp to use: '
        )
        choice = choose_multiple(msg, (1, 2, 3))
        if choice == 1:
            if not our_started:
                print('Chose our timestamp but we got no timestamp. Bailing ...')
                sys.exit(1)
            timestamp = our_started

        elif choice == 2:
            if not paprika_started_ts:
                print("Chose coin paprika's timestamp but it's empty. Bailing ...")
                sys.exit(1)
            timestamp = paprika_started_ts

        elif choice == 3:
            if not cmc_started_ts:
                print("Chose coinmarketcap's timestamp but it's empty. Bailing ...")
                sys.exit(1)
            timestamp = cmc_started_ts

        our_data[asset_symbol]['started'] = timestamp

    return our_data
