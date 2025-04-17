import json
import random
from pathlib import Path
from typing import Any

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.kraken import Kraken
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.factories import (
    make_random_positive_fval,
    make_random_timestamp,
    make_random_uppercasenumeric_string,
)
from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import jsonloads_dict

KRAKEN_DELISTED = (
    'XDAO',
    'XXVN',
    'ZKRW',
    'XNMC',
    'BSV',
    'XICN',
    'PLA',
    'WAVES',
)

KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE = """{
    "trades": {
        "1": {
            "ordertxid": "1",
            "postxid": 1,
            "pair": "XXBTZEUR",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""},
        "2": {
            "ordertxid": "2",
            "postxid": 2,
            "pair": "XETHZEUR",
            "time": "1456994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""},
        "3": {
            "ordertxid": "3",
            "postxid": 3,
            "pair": "IDONTEXISTZEUR",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""
        },
        "4": {
            "ordertxid": "4",
            "postxid": 4,
            "pair": "XETHIDONTEXISTTOO",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""
        },
        "5": {
            "ordertxid": "5",
            "postxid": 5,
            "pair": "%$#%$#%$#%$#%$#%",
            "time": "1458994442.0000",
            "type": "buy",
            "ordertype": "market",
            "price": "100",
            "vol": "1",
            "fee": "0.1",
            "cost": "100",
            "margin": "0.0",
            "misc": ""
        }},
    "count": 5
}"""

KRAKEN_SPECIFIC_DEPOSITS_RESPONSE = """
      {
            "ledger": {
                "1": {
                    "refid": "1",
                    "time": "1458994442",
                    "type": "deposit",
                    "aclass": "currency",
                    "asset": "BTC",
                    "amount": "5.0",
                    "balance": "10.0",
                    "fee": "0.1"
                },
                "2": {
                    "refid": "2",
                    "time": "1448994442",
                    "type": "deposit",
                    "aclass": "currency",
                    "asset": "ETH",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                },
                "3": {
                    "refid": "3",
                    "time": "1438994442",
                    "type": "deposit",
                    "aclass": "currency",
                    "asset": "IDONTEXIST",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                }
            },
            "count": 3
}"""

KRAKEN_SPECIFIC_WITHDRAWALS_RESPONSE = """
{
            "ledger": {
                "4": {
                    "refid": "4",
                    "time": "1428994442",
                    "type": "withdrawal",
                    "aclass": "currency",
                    "asset": "BTC",
                    "amount": "5.0",
                    "balance": "10.0",
                    "fee": "0.1"
                },
                "5": {
                    "refid": "5",
                    "time": "1439994442",
                    "type": "withdrawal",
                    "aclass": "currency",
                    "asset": "ETH",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                },
                "6": {
                    "refid": "6",
                    "time": "1408994442",
                    "type": "withdrawal",
                    "aclass": "currency",
                    "asset": "IDONTEXISTEITHER",
                    "amount": "10.0",
                    "balance": "100.0",
                    "fee": "0.11"
                }
            },
            "count": 3
}"""

KRAKEN_GENERAL_LEDGER_RESPONSE = """
{
    "ledger": {
        "L12382343925": {
            "refid": "D1",
            "time": 1458994442,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "BTC",
            "amount": "5.0",
            "fee": "0",
            "balance": "10"
        },
        "L12382343926": {
            "refid": "D2",
            "time": 1448994442,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "ETH",
            "amount": "10.0000",
            "fee": "0",
            "balance": "100.25"
        },
        "L12382343927": {
            "refid": "D3",
            "time": 1408994442,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "IDONTEXISTEITHER",
            "amount": "10",
            "fee": "0",
            "balance": "100"
        },
        "L12382343965": {
            "refid": "W1",
            "time": 1428994442,
            "type": "withdrawal",
            "subtype": "",
            "aclass": "currency",
            "asset": "BTC",
            "amount": "-5.0",
            "fee": "0.1",
            "balance": "10"
        },
        "L12382343966": {
            "refid": "W2",
            "time": 1439994442,
            "type": "withdrawal",
            "subtype": "",
            "aclass": "currency",
            "asset": "ETH",
            "amount": "-10.0000",
            "fee": "1.7500",
            "balance": "100.25"
        },
        "L12382343967": {
            "refid": "W3",
            "time": 1408994442,
            "type": "withdrawal",
            "subtype": "",
            "aclass": "currency",
            "asset": "IDONTEXISTEITHER",
            "amount": "-10",
            "fee": "0.11",
            "balance": "100"
        },
        "L1": {
            "refid": "AOEXXV-61T63-AKPSJ0",
            "time": 1609950165.4497,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "KFEE",
            "amount": "0.00",
            "fee": "0.11",
            "balance": "100"
        },
        "L2": {
            "refid": "AOEXXV-61T63-AKPSJ0",
            "time": 1609950165.4492,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "ZEUR",
            "amount": "50",
            "fee": "0.4429",
            "balance": "500"
        },
        "L3": {
            "refid": "AOEXXV-61T63-AKPSJ0",
            "time": 1609950165.4486,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "XETH",
            "amount": "-0.1",
            "fee": "0.0000000000",
            "balance": 1.1
        },
        "0": {
            "refid": "2",
            "time": 1439994442,
            "type": "withdrawal",
            "subtype": "",
            "aclass": "currency",
            "asset": "XETH",
            "amount": "-1.0000000000",
            "fee": "0.0035000000",
            "balance": "0.0000100000"
        },
        "L343242342": {
            "refid": "1",
            "time": 1458994442.064,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "XXBT",
            "amount": "1",
            "fee": "0.0000000000",
            "balance": "0.0437477300"
        },
        "L5354645643": {
            "refid": "1",
            "time": 1458994442.063,
            "type": "trade",
            "subtype": "",
            "aclass": "currency",
            "asset": "ZEUR",
            "amount": "-100",
            "fee": "0.1",
            "balance": "200"
        },
        "L12382343902": {
            "refid": "0",
            "time": 1458994441.396,
            "type": "deposit",
            "subtype": "",
            "aclass": "currency",
            "asset": "EUR.HOLD",
            "amount": "4000000.0000",
            "fee": "1.7500",
            "balance": "3999998.25"
        }
    },
    "count": 13
}
"""


def get_kraken_assets_from_globaldb() -> list[str]:
    with GlobalDBHandler().conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT exchange_symbol FROM location_asset_mappings WHERE location IS ? OR location IS NULL;',  # noqa: E501
            (Location.KRAKEN.serialize_for_db(),),
        ).fetchall()


def get_random_kraken_asset() -> str:
    kraken_assets = set(get_kraken_assets_from_globaldb()) - set(KRAKEN_DELISTED)
    return random.choice(list(kraken_assets))


def generate_random_kraken_balance_response() -> dict[str, FVal]:
    kraken_assets = set(get_kraken_assets_from_globaldb()) - set(KRAKEN_DELISTED)
    number_of_assets = random.randrange(0, len(kraken_assets))
    chosen_assets = random.sample(list(kraken_assets), number_of_assets)

    balances = {}
    for asset in chosen_assets:
        balances[asset] = make_random_positive_fval()

    return balances


def generate_random_kraken_id() -> str:
    return (
        make_random_uppercasenumeric_string(6) + '-' +
        make_random_uppercasenumeric_string(5) + '-' +
        make_random_uppercasenumeric_string(6)
    )


def get_exchange_name_from_assetid(exchange: Location, asset_identifier: str) -> str | None:
    """Returns the ticker symbol used in the given exchange from asset's identifier according
        to location_asset_mappings table. If the mapping is not present returns None."""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        identifier = cursor.execute(
            'SELECT exchange_symbol FROM location_asset_mappings WHERE (location IS ? OR location IS NULL) AND local_id=?',  # noqa: E501
            (exchange.serialize_for_db(), asset_identifier),
        ).fetchone()

        return None if identifier is None else identifier[0]


def create_kraken_trade(
        tradeable_pairs: list[str],
        base_asset: str | None = None,
        quote_asset: str | None = None,
        time: Timestamp | None = None,
        start_ts: Timestamp | None = None,
        end_ts: Timestamp | None = None,
        rate: FVal | None = None,
        amount: FVal | None = None,
        fee: FVal | None = None,
) -> dict[str, str]:
    trade = {}
    trade['ordertxid'] = str(generate_random_kraken_id())
    trade['postxid'] = str(generate_random_kraken_id())
    if base_asset is None or quote_asset is None:
        pair = random.choice(tradeable_pairs)
    else:
        base_symbol = get_exchange_name_from_assetid(
            exchange=Location.KRAKEN,
            asset_identifier=base_asset,
        )
        quote_symbol = get_exchange_name_from_assetid(
            exchange=Location.KRAKEN,
            asset_identifier=quote_asset,
        )
        assert base_symbol is not None
        assert quote_symbol is not None
        pair = base_symbol + quote_symbol

    trade['pair'] = pair
    if time:
        trade['time'] = str(time) + '.0000'
    else:
        trade['time'] = str(make_random_timestamp(start=start_ts, end=end_ts)) + '.0000'

    trade['type'] = random.choice(('buy', 'sell'))
    trade['ordertype'] = random.choice(('limit', 'market'))
    if rate:
        price = rate
    else:
        price = make_random_positive_fval()
    trade['price'] = str(price)

    if amount:
        volume = amount
    else:
        volume = make_random_positive_fval()
    trade['vol'] = str(volume)

    if fee:
        trade['fee'] = str(fee)
    else:
        trade['fee'] = str(make_random_positive_fval(max_num=2))

    trade['fee'] = str(make_random_positive_fval(max_num=2))
    trade['cost'] = str(price * volume)
    trade['margin'] = '0.0'
    trade['misc'] = ''
    return trade


def generate_random_kraken_trade_data(
        tradeable_pairs: list[str],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> dict[str, str]:
    return create_kraken_trade(
        tradeable_pairs=tradeable_pairs,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def generate_random_single_kraken_ledger_data(
        start_ts: Timestamp,
        end_ts: Timestamp,
        ledger_type: str,
) -> dict[str, str]:
    ledger = {}
    ledger['refid'] = str(generate_random_kraken_id())
    ledger['time'] = str(make_random_timestamp(start=start_ts, end=end_ts)) + '.0000'
    ledger['type'] = ledger_type
    ledger['aclass'] = 'currency'
    ledger['asset'] = get_random_kraken_asset()
    ledger['amount'] = str(make_random_positive_fval())
    ledger['balance'] = str(make_random_positive_fval())
    ledger['fee'] = str(make_random_positive_fval(max_num=2))
    return ledger


def generate_random_kraken_ledger_data(start: Timestamp, end: Timestamp, ledger_type: str):
    ledgers_num = random.randint(1, 49)
    # Ledgers is a dict with txid as the key
    ledgers = {}
    for _ in range(ledgers_num):
        ledger = generate_random_single_kraken_ledger_data(
            start_ts=start,
            end_ts=end,
            ledger_type=ledger_type,
        )
        ledgers[ledger['refid']] = ledger

    response_str = json.dumps({'ledger': ledgers, 'count': ledgers_num})
    return json.loads(response_str)


def generate_random_kraken_trades_data(
        start: Timestamp,
        end: Timestamp,
        tradeable_pairs: list[str],
):
    trades_num = random.randint(1, 49)

    # Trades is a dict with txid as the key
    trades = {}
    for _ in range(trades_num):
        trade = generate_random_kraken_trade_data(
            tradeable_pairs,
            start,
            end,
        )
        trades[trade['ordertxid']] = trade

    response_str = json.dumps({'trades': trades, 'count': trades_num})
    return json.loads(response_str)


class MockKraken(Kraken):

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )

        self.random_trade_data = True
        self.random_balance_data = True
        self.random_ledgers_data = False
        self.remote_errors = False
        self.use_original_kraken = False

        self.balance_data_return = {'XXBT': '5.0', 'XETH': '10.0', 'NOTAREALASSET': '15.0'}
        # Not required in the real Kraken instance but we use it in the tests
        self.tradeable_pairs = self.api_query('AssetPairs')

    @staticmethod
    def _load_results_from_file(filename: str) -> dict[str, Any]:
        dir_path = Path(__file__).resolve().parent.parent
        return jsonloads_dict((dir_path / 'data' / filename).read_text(encoding='utf8'))

    def api_query(self, method: str, req: dict | None = None) -> dict:
        # Pretty ugly ... mock a kraken remote error
        if self.remote_errors:
            raise RemoteError('Kraken remote error')

        if self.use_original_kraken:
            return super().api_query(method, req)

        if method == 'Balance':
            if self.random_balance_data:
                return generate_random_kraken_balance_response()
            # else
            return self.balance_data_return
        if method == 'TradesHistory':
            assert req, 'Should have given arguments for kraken TradesHistory endpoint call'
            if self.random_trade_data:
                return generate_random_kraken_trades_data(
                    start=req['start'],
                    end=req['end'],
                    tradeable_pairs=list(self.tradeable_pairs.keys()),
                )
            # else
            return jsonloads_dict(KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE)
        if method == 'AssetPairs':
            data = self._load_results_from_file('assets_kraken.json')
            return data['result']
        if method == 'Assets':
            data = self._load_results_from_file('assets_only_kraken.json')
            return data['result']
        if method == 'Ledgers':
            if req is None:
                req = {}
            ledger_type: str = req.get('type', '')
            if self.random_ledgers_data:
                assert req is not None
                return generate_random_kraken_ledger_data(
                    start=req.get('start', 0),
                    end=req.get('end', ts_now),
                    ledger_type=ledger_type,
                )

            # else use specific data
            if ledger_type in {'deposit', 'withdrawal'}:
                data = json.loads(
                    KRAKEN_SPECIFIC_DEPOSITS_RESPONSE if ledger_type == 'deposit'
                    else KRAKEN_SPECIFIC_WITHDRAWALS_RESPONSE,
                )
            else:
                data = json.loads(KRAKEN_GENERAL_LEDGER_RESPONSE)
            new_data: dict[str, Any] = {'ledger': {}}
            for key, val in data['ledger'].items():
                try:
                    ts = int(val['time'])
                except ValueError:
                    # can happen for tests of invalid data -- let it through
                    ts = req.get('start', 0)
                if ts < req.get('start', 0) or ts > req.get('end', ts_now):
                    continue
                new_data['ledger'][key] = val

            new_data['count'] = len(new_data['ledger'])
            response = json.dumps(new_data)
            return jsonloads_dict(response)
        # else
        return super().api_query(method, req)
