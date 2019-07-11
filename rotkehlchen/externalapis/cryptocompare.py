import glob
import logging
import os
import re
import time
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, NamedTuple, NewType

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.constants.cryptocompare import KNOWN_TO_MISS_FROM_CRYPTOCOMPARE
from rotkehlchen.errors import PriceQueryUnknownFromAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath, Price, Timestamp
from rotkehlchen.utils.misc import (
    convert_to_int,
    request_get_dict,
    ts_now,
    tsToDate,
    write_history_data_in_file,
)
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


T_PairCacheKey = str
PairCacheKey = NewType('PairCacheKey', T_PairCacheKey)


class PriceHistoryEntry(NamedTuple):
    time: Timestamp
    low: Price
    high: Price


class PriceHistoryData(NamedTuple):
    data: List[PriceHistoryEntry]
    start_time: Timestamp
    end_time: Timestamp


class NoPriceForGivenTimestamp(Exception):
    def __init__(self, from_asset, to_asset, timestamp):
        super(NoPriceForGivenTimestamp, self).__init__(
            'Unable to query a historical price for "{}" to "{}" at {}'.format(
                from_asset, to_asset, timestamp,
            ),
        )


def _dict_history_to_entries(data: List[Dict[str, Any]]) -> List[PriceHistoryEntry]:
    """Turns a list of dict of history entries to a list of proper objects"""
    return [
        PriceHistoryEntry(
            time=Timestamp(entry['time']),
            low=Price(entry['low']),
            high=Price(entry['high']),
        ) for entry in data
    ]


def _dict_history_to_data(data: Dict[str, Any]) -> PriceHistoryData:
    """Turns a price history data dict entry into a proper object"""
    return PriceHistoryData(
        data=_dict_history_to_entries(data['data']),
        start_time=Timestamp(data['start_time']),
        end_time=Timestamp(data['end_time']),
    )


def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)


def _check_hourly_data_sanity(data, from_asset, to_asset):
    """Check that the hourly data is an array of objects having timestamps
    increasing by 1 hour.
    """
    index = 0
    for n1, n2 in pairwise(data):
        diff = n2['time'] - n1['time']
        if diff != 3600:
            print(
                "Problem at indices {} and {} of {}_to_{} prices. Time difference is: {}".format(
                    index, index + 1, from_asset, to_asset, diff),
            )
            return False

        index += 2
    return True


class Cryptocompare():

    def __init__(self, data_directory: FilePath) -> None:
        self.prefix = 'https://min-api.cryptocompare.com/data/'
        self.data_directory = data_directory
        self.price_history: Dict[PairCacheKey, PriceHistoryData] = dict()
        self.price_history_file: Dict[PairCacheKey, FilePath] = dict()

        # Check the data folder and remember the filenames of any cached history
        prefix = os.path.join(self.data_directory, 'price_history_')
        prefix = prefix.replace('\\', '\\\\')
        regex = re.compile(prefix + r'(.*)\.json')
        files_list = glob.glob(prefix + '*.json')

        for file_ in files_list:
            file_ = FilePath(file_.replace('\\\\', '\\'))
            match = regex.match(file_)
            assert match
            cache_key = PairCacheKey(match.group(1))
            self.price_history_file[cache_key] = file_

    def _api_query(self, path: str, only_data: bool = True) -> Dict[str, Any]:
        querystr = f'{self.prefix}{path}'
        log.debug('Querying cryptocompare', url=querystr)
        resp = request_get_dict(querystr)
        if 'Response' not in resp or resp['Response'] != 'Success':
            error_message = 'Failed to query cryptocompare for: "{}"'.format(querystr)
            if 'Message' in resp:
                error_message += ". Error: {}".format(resp['Message'])

            log.error('Cryptocompare query failure', url=querystr, error=error_message)
            raise ValueError(error_message)

        if only_data:
            return resp['Data']

        return resp

    def query_endpoint_histohour(
            self,
            from_asset: Asset,
            to_asset: Asset,
            limit: int,
            to_timestamp: Timestamp,
    ) -> Dict[str, Any]:
        # These two can raise but them raising here is a bug
        cc_from_asset_symbol = from_asset.to_cryptocompare()
        cc_to_asset_symbol = to_asset.to_cryptocompare()
        query_path = (
            f'histohour?fsym={cc_from_asset_symbol}&tsym={cc_to_asset_symbol}'
            f'&limit={limit}&toTs={to_timestamp}'
        )
        result = self._api_query(path=query_path, only_data=False)
        return result

    def query_endpoint_pricehistorical(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        log.debug(
            'Querying cryptocompare for daily historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        # These two can raise but them raising here is a bug
        cc_from_asset_symbol = from_asset.to_cryptocompare()
        cc_to_asset_symbol = to_asset.to_cryptocompare()
        query_path = (
            f'pricehistorical?fsym={cc_from_asset_symbol}&tsyms={cc_to_asset_symbol}'
            f'&ts={timestamp}'
        )
        if to_asset == 'BTC':
            query_path += '&tryConversion=false'
        result = self._api_query(query_path)
        return Price(FVal(result[cc_from_asset_symbol][cc_to_asset_symbol]))

    def got_cached_price(self, cache_key: PairCacheKey, timestamp: Timestamp) -> bool:
        """Check if we got a price history for the timestamp cached"""
        if cache_key in self.price_history_file:
            if cache_key not in self.price_history:
                try:
                    with open(self.price_history_file[cache_key], 'r') as f:
                        data = rlk_jsonloads_dict(f.read())
                        self.price_history[cache_key] = _dict_history_to_data(data)
                except (OSError, IOError, JSONDecodeError):
                    return False

            in_range = (
                self.price_history[cache_key].start_time <= timestamp and
                self.price_history[cache_key].end_time > timestamp
            )
            if in_range:
                log.debug('Found cached price', cache_key=cache_key, timestamp=timestamp)
                return True

        return False

    def get_historical_data(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            historical_data_start: Timestamp,
    ) -> List[PriceHistoryEntry]:
        """
        Get historical price data from cryptocompare

        Returns a sorted list of price entries.
        """
        log.debug(
            'Retrieving historical price data from cryptocompare',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

        cache_key = PairCacheKey(str(from_asset) + '_' + str(to_asset))
        got_cached_value = self.got_cached_price(cache_key, timestamp)
        if got_cached_value:
            return self.price_history[cache_key].data

        now_ts = int(time.time())
        cryptocompare_hourquerylimit = 2000
        calculated_history: List = list()

        if historical_data_start <= timestamp:
            end_date = historical_data_start
        else:
            end_date = timestamp
        while True:
            pr_end_date = end_date
            end_date = Timestamp(end_date + (cryptocompare_hourquerylimit) * 3600)

            log.debug(
                'Querying cryptocompare for hourly historical price',
                from_asset=from_asset,
                to_asset=to_asset,
                cryptocompare_hourquerylimit=cryptocompare_hourquerylimit,
                end_date=end_date,
            )

            resp = self.query_endpoint_histohour(
                from_asset=from_asset,
                to_asset=to_asset,
                limit=2000,
                to_timestamp=end_date,
            )

            if pr_end_date != resp['TimeFrom']:
                # If we get more than we needed, since we are close to the now_ts
                # then skip all the already included entries
                diff = pr_end_date - resp['TimeFrom']
                if resp['Data'][diff // 3600]['time'] != pr_end_date:
                    raise ValueError(
                        'Expected to find the previous date timestamp during '
                        'historical data fetching',
                    )
                # just add only the part from the previous timestamp and on
                resp['Data'] = resp['Data'][diff // 3600:]

            if end_date < now_ts and resp['TimeTo'] != end_date:
                raise ValueError('End dates no match')

            # If last time slot and first new are the same, skip the first new slot
            last_entry_equal_to_first = (
                len(calculated_history) != 0 and
                calculated_history[-1]['time'] == resp['Data'][0]['time']
            )
            if last_entry_equal_to_first:
                resp['Data'] = resp['Data'][1:]
            calculated_history += resp['Data']
            if end_date >= now_ts:
                break

        # Let's always check for data sanity for the hourly prices.
        assert _check_hourly_data_sanity(calculated_history, from_asset, to_asset)
        # and now since we actually queried the data let's also cache them
        filename = FilePath(
            os.path.join(self.data_directory, 'price_history_' + cache_key + '.json'),
        )
        log.info(
            'Updating price history cache',
            filename=filename,
            from_asset=from_asset,
            to_asset=to_asset,
        )
        write_history_data_in_file(
            data=calculated_history,
            filepath=filename,
            start_ts=historical_data_start,
            end_ts=now_ts,
        )

        # Finally save the objects in memory and return them
        data_including_time = {
            'data': calculated_history,
            'start_time': historical_data_start,
            'end_time': end_date,
        }
        self.price_history_file[cache_key] = filename
        self.price_history[cache_key] = _dict_history_to_data(data_including_time)

        return self.price_history[cache_key].data

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            historical_data_start: Timestamp,
    ) -> Price:
        if from_asset in KNOWN_TO_MISS_FROM_CRYPTOCOMPARE:
            raise PriceQueryUnknownFromAsset(from_asset)

        data = self.get_historical_data(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            historical_data_start=historical_data_start,
        )

        # all data are sorted and timestamps are always increasing by 1 hour
        # find the closest entry to the provided timestamp
        if timestamp >= data[0].time:
            index = convert_to_int((timestamp - data[0].time) / 3600, accept_only_exact=False)
            # print("timestamp: {} index: {} data_length: {}".format(timestamp, index, len(data)))
            diff = abs(data[index].time - timestamp)
            if index + 1 <= len(data) - 1:
                diff_p1 = abs(data[index + 1].time - timestamp)
                if diff_p1 < diff:
                    index = index + 1

            if data[index].high is None or data[index].low is None:
                # If we get some None in the hourly set price to 0 so that we check alternatives
                price = Price(ZERO)
            else:
                price = (data[index].high + data[index].low) / 2
        else:
            # no price found in the historical data from/to asset, try alternatives
            price = Price(ZERO)

        if price == 0:
            if from_asset != 'BTC' and to_asset != 'BTC':
                log.debug(
                    f"Couldn't find historical price from {from_asset} to "
                    f"{to_asset} at timestamp {timestamp}. Comparing with BTC...",
                )
                # Just get the BTC price
                asset_btc_price = PriceHistorian().query_historical_price(
                    from_asset=from_asset,
                    to_asset=A_BTC,
                    timestamp=timestamp,
                )
                btc_to_asset_price = PriceHistorian().query_historical_price(
                    from_asset=A_BTC,
                    to_asset=to_asset,
                    timestamp=timestamp,
                )
                price = asset_btc_price * btc_to_asset_price
            else:
                log.debug(
                    f"Couldn't find historical price from {from_asset} to "
                    f"{to_asset} at timestamp {timestamp} through cryptocompare."
                    f" Attempting to get daily price...",
                )
                price = self.query_endpoint_pricehistorical(from_asset, to_asset, timestamp)

        comparison_to_nonusd_fiat = (
            (to_asset.is_fiat() and to_asset != A_USD) or
            (from_asset.is_fiat() and from_asset != A_USD)
        )
        if comparison_to_nonusd_fiat:
            price = self._adjust_to_cryptocompare_price_incosistencies(
                price=price,
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        if price == 0:
            raise NoPriceForGivenTimestamp(
                from_asset,
                to_asset,
                tsToDate(timestamp, formatstr='%d/%m/%Y, %H:%M:%S'),
            )

        log.debug(
            'Got historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            price=price,
        )

        return price

    @staticmethod
    def _adjust_to_cryptocompare_price_incosistencies(
            price: Price,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """Doublecheck against the USD rate, and if incosistencies are found
        then take the USD adjusted price.

        This is due to incosistencies in the provided historical data from
        cryptocompare. https://github.com/rotkehlchenio/rotkehlchen/issues/221

        Note: Since 12/01/2019 this seems to no longer be happening, but I will
        keep the code around just in case a regression is introduced on the side
        of cryptocompare.
        """
        from_asset_usd = PriceHistorian().query_historical_price(
            from_asset=from_asset,
            to_asset=A_USD,
            timestamp=timestamp,
        )
        to_asset_usd = PriceHistorian().query_historical_price(
            from_asset=to_asset,
            to_asset=A_USD,
            timestamp=timestamp,
        )

        usd_invert_conversion = from_asset_usd / to_asset_usd
        abs_diff = abs(usd_invert_conversion - price)
        relative_difference = abs_diff / max(price, usd_invert_conversion)
        if relative_difference >= FVal('0.1'):
            log.warning(
                'Cryptocompare historical price data are incosistent.'
                'Taking USD adjusted price. Check github issue #221',
                from_asset=from_asset,
                to_asset=to_asset,
                incosistent_price=price,
                usd_price=from_asset_usd,
                adjusted_price=usd_invert_conversion,
            )
            return usd_invert_conversion
        return price

    def all_coins(self) -> Dict[str, Any]:
        """Gets the list of all the cryptocompare coins"""
        # Get coin list of crypto compare
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cryptocompare_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found cryptocompare coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'r') as f:
                try:
                    data = rlk_jsonloads_dict(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery cryptocompare
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Cryptocompare coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            data = self._api_query('all/coinlist')

            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        # As described in the docs
        # https://min-api.cryptocompare.com/documentation?key=Other&cat=allCoinsWithContentEndpoint
        # This is not the entire list of assets in the system, so I am manually adding
        # here assets I am aware of that they already have historical data for in thei
        # cryptocompare system
        data['DAO'] = object()
        data['USDT'] = object()
        data['VEN'] = object()
        data['AIR*'] = object()  # This is Aircoin
        # This is SpendCoin (https://coinmarketcap.com/currencies/spendcoin/)
        data['SPND'] = object()
        # This is eBitcoinCash (https://coinmarketcap.com/currencies/ebitcoin-cash/)
        data['EBCH'] = object()
        # This is Educare (https://coinmarketcap.com/currencies/educare/)
        data['EKT'] = object()
        # This is Fidelium (https://coinmarketcap.com/currencies/fidelium/)
        data['FID'] = object()
        # This is Knoxstertoken (https://coinmarketcap.com/currencies/knoxstertoken/)
        data['FKX'] = object()
        # This is FNKOS (https://coinmarketcap.com/currencies/fnkos/)
        data['FNKOS'] = object()
        # This is FansTime (https://coinmarketcap.com/currencies/fanstime/)
        data['FTI'] = object()
        # This is Gene Source Code Chain
        # (https://coinmarketcap.com/currencies/gene-source-code-chain/)
        data['GENE*'] = object()
        # This is GazeCoin (https://coinmarketcap.com/currencies/gazecoin/)
        data['GZE'] = object()
        # This is probaly HarmonyCoin (https://coinmarketcap.com/currencies/harmonycoin-hmc/)
        data['HMC*'] = object()
        # This is IoTChain (https://coinmarketcap.com/currencies/iot-chain/)
        data['ITC'] = object()
        # This is MFTU (https://coinmarketcap.com/currencies/mainstream-for-the-underground/)
        data['MFTU'] = object()
        # This is Nexxus (https://coinmarketcap.com/currencies/nexxus/)
        data['NXX'] = object()
        # This is Owndata (https://coinmarketcap.com/currencies/owndata/)
        data['OWN'] = object()
        # This is PiplCoin (https://coinmarketcap.com/currencies/piplcoin/)
        data['PIPL'] = object()
        # This is PKG Token (https://coinmarketcap.com/currencies/pkg-token/)
        data['PKG'] = object()
        # This is Quibitica https://coinmarketcap.com/currencies/qubitica/
        data['QBIT'] = object()
        # This is DPRating https://coinmarketcap.com/currencies/dprating/
        data['RATING'] = object()
        # This is RouletteToken https://coinmarketcap.com/currencies/roulettetoken/
        data['RLT'] = object()
        # This is RocketPool https://coinmarketcap.com/currencies/rocket-pool/
        data['RPL'] = object()
        # This is SpeedMiningService (https://coinmarketcap.com/currencies/speed-mining-service/)
        data['SMS'] = object()
        # This is SmartShare (https://coinmarketcap.com/currencies/smartshare/)
        data['SSP'] = object()
        # This is ThoreCoin (https://coinmarketcap.com/currencies/thorecoin/)
        data['THR'] = object()
        # This is Transcodium (https://coinmarketcap.com/currencies/transcodium/)
        data['TNS'] = object()
        # This is XMedChainToken (https://coinmarketcap.com/currencies/xmct/)
        data['XMCT'] = object()
        # This is Xplay (https://coinmarketcap.com/currencies/xpa)
        data['XPA'] = object()

        return data
