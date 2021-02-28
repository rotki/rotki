import sys
from typing import Any, Dict

from asset_aggregator.utils import choose_multiple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.typing import EthAddress, Timestamp
from rotkehlchen.utils.misc import create_timestamp, iso8601ts_to_timestamp, timestamp_to_date
from rotkehlchen.utils.network import request_get_dict

# For these assets we will definitely always use our data as they are more accurate
# than coin paprika or cryptocompare or we have already decided on a time
# so querying should be skipped
PREFER_OUR_STARTED = (
    # For all assets below not much research, just took the earliest one
    'ADA',
    'EOS',
    'ICN',
    'MLN',
    'QTUM',
    'REP',
    'USDT',
    'XRP',
    'XTZ',
    'ABY',

    # Taken from here: https://neotracker.io/asset/a0777c3ce2b169d4a23bcba4565e3225a0122d95
    'APH',
    # Taking coin paprika's data here
    'ETH',
    # We use the exact timestamp of the BSV block fork
    'BSV',
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


def get_token_contract_creation_time(token_address: str) -> Timestamp:
    resp = request_get_dict(
        f'http://api.etherscan.io/api?module=account&action=txlist&address='
        f'{token_address}&startblock=0&endblock=999999999&sort=asc',
    )
    if resp['status'] != 1:
        raise ValueError('Failed to query etherscan for token {token_address} creation')
    tx_list = resp['result']
    if len(tx_list) == 0:
        raise ValueError('Etherscan query of {token_address} transactions returned empty list')

    return Timestamp(tx_list[0]['timeStamp'].to_int(exact=True))


def timerange_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
        always_keep_our_time: bool,
        token_address: EthAddress = None,
) -> Dict[str, Any]:
    """Process the started timestamps from coin paprika and coinmarketcap.

    Then compare to our data and provide choices to clean up the data.
    """
    if Asset(asset_symbol).is_fiat():
        # Fiat does not have started date (or we don't care about it)
        return our_data

    paprika_started = None
    if paprika_data:
        paprika_started = paprika_data['started_at']
    cmc_started = None
    if cmc_data:
        cmc_started = cmc_data['first_historical_data']

    if not cmc_started and not paprika_started and not token_address:
        print(f'Did not find a started date for asset {asset_symbol} in any of the external APIs')
        return our_data

    paprika_started_ts = None
    if paprika_started:
        paprika_started_ts = create_timestamp(paprika_started, formatstr='%Y-%m-%dT%H:%M:%SZ')
    cmc_started_ts = None
    if cmc_data:
        cmc_started_ts = iso8601ts_to_timestamp(cmc_started)

    if asset_symbol in PREFER_OUR_STARTED:
        assert 'started' in our_asset
        # Already manually checked
        return our_data

    our_started = our_asset.get('started', None)

    # if it's an eth token entry, get the contract creation time too
    if token_address:
        contract_creation_ts = get_token_contract_creation_time(token_address)

    if not our_started:
        # If we don't have any data and CMC and paprika agree just use their timestamp
        if cmc_started == paprika_started and cmc_started is not None:
            our_data[asset_symbol]['started'] = cmc_started
            return our_data

    if our_started and always_keep_our_time:
        return our_data

    if our_started is None or our_started != cmc_started or our_started != paprika_started:
        choices = (1, 2, 3)
        msg = (
            f'For asset {asset_symbol} the started times are: \n'
            f'(1) Our data: {our_started} -- {timestamp_to_date(our_started) if our_started else ""}\n'
            f'(2) Coinpaprika: {paprika_started_ts} -- '
            f'{timestamp_to_date(paprika_started_ts) if paprika_started_ts else ""}\n'
            f'(3) Coinmarketcap: {cmc_started_ts} -- '
            f'{timestamp_to_date(cmc_started_ts) if cmc_started_ts else ""} \n'
        )
        if token_address:
            msg += (
                f'(4) Contract creation: {contract_creation_ts} -- '
                f'{timestamp_to_date(contract_creation_ts) if contract_creation_ts else ""}\n'
            )
            choices = (1, 2, 3, 4)

        msg += f'Choose a number (1)-({choices[-1]}) to choose which timestamp to use: '
        choice = choose_multiple(msg, choices)
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

        elif choice == 4:
            if not contract_creation_ts:
                print("Chose contract creation timestamp but it's empty. Bailing ...")
                sys.exit(1)
            timestamp = contract_creation_ts

        our_data[asset_symbol]['started'] = timestamp

    return our_data
