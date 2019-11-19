import json
import random
from typing import Dict, List, Optional

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import KRAKEN_TO_WORLD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import TradeType
from rotkehlchen.exchanges.kraken import KRAKEN_DELISTED, Kraken, world_to_kraken_pair
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import (
    KRAKEN_SPECIFIC_DEPOSITS_RESPONSE,
    KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE,
    KRAKEN_SPECIFIC_WITHDRAWALS_RESPONSE,
)
from rotkehlchen.tests.utils.factories import (
    make_api_key,
    make_api_secret,
    make_random_positive_fval,
    make_random_timestamp,
    make_random_uppercasenumeric_string,
)
from rotkehlchen.typing import ApiKey, ApiSecret, Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.serialization import rlk_jsonloads


def get_random_kraken_asset() -> Asset:
    kraken_assets = set(KRAKEN_TO_WORLD.keys()) - set(KRAKEN_DELISTED)
    return random.choice(list(kraken_assets))


def generate_random_kraken_balance_response():
    kraken_assets = set(KRAKEN_TO_WORLD.keys()) - set(KRAKEN_DELISTED)
    number_of_assets = random.randrange(0, len(kraken_assets))
    chosen_assets = random.sample(kraken_assets, number_of_assets)

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


def create_kraken_trade(
        tradeable_pairs: List[str],
        pair: Optional[TradePair] = None,
        time: Optional[Timestamp] = None,
        start_ts: Optional[Timestamp] = None,
        end_ts: Optional[Timestamp] = None,
        trade_type: Optional[TradeType] = None,
        rate: Optional[FVal] = None,
        amount: Optional[FVal] = None,
        fee: Optional[FVal] = None,
) -> Dict[str, str]:
    trade = {}
    trade['ordertxid'] = str(generate_random_kraken_id())
    trade['postxid'] = str(generate_random_kraken_id())
    if pair:
        trade['pair'] = world_to_kraken_pair(tradeable_pairs=tradeable_pairs, pair=pair)
    else:
        trade['pair'] = random.choice(tradeable_pairs)
    if time:
        trade['time'] = str(time) + '.0000'
    else:
        trade['time'] = str(make_random_timestamp(start=start_ts, end=end_ts)) + '.0000'
    if trade_type:
        trade['type'] = str(trade_type)
    else:
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
        tradeable_pairs: List[str],
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> Dict[str, str]:
    return create_kraken_trade(
        tradeable_pairs=tradeable_pairs,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def generate_random_single_kraken_ledger_data(
        start_ts: Timestamp,
        end_ts: Timestamp,
        ledger_type: str,
) -> Dict[str, str]:
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


def generate_random_kraken_ledger_data(start: Timestamp, end: Timestamp, ledger_type):
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
    return rlk_jsonloads(response_str)


def generate_random_kraken_trades_data(
        start: Timestamp,
        end: Timestamp,
        tradeable_pairs: List[str],
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
    return rlk_jsonloads(response_str)


class MockKraken(Kraken):

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super(MockKraken, self).__init__(
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )

        self.random_trade_data = True
        self.random_balance_data = True
        self.random_ledgers_data = True
        self.remote_errors = False

        self.balance_data_return = {'XXBT': '5.0', 'XETH': '10.0', 'NOTAREALASSET': '15.0'}
        # Not required in the real Kraken instance but we use it in the tests
        self.tradeable_pairs = self.query_public('AssetPairs')

    def query_private(self, method: str, req: Optional[dict] = None) -> dict:
        # Pretty ugly ... mock a kraken remote eror
        if self.remote_errors:
            raise RemoteError('Kraken remote error')

        if method == 'Balance':
            if self.random_balance_data:
                return generate_random_kraken_balance_response()
            # else
            return self.balance_data_return
        elif method == 'TradesHistory':
            if self.random_trade_data:
                return generate_random_kraken_trades_data(
                    start=req['start'],
                    end=req['end'],
                    tradeable_pairs=list(self.tradeable_pairs.keys()),
                )
            # else
            return rlk_jsonloads(KRAKEN_SPECIFIC_TRADES_HISTORY_RESPONSE)
        elif method == 'Ledgers':
            ledger_type = req['type']
            if self.random_ledgers_data:
                return generate_random_kraken_ledger_data(
                    start=req['start'],
                    end=req['end'],
                    ledger_type=ledger_type,
                )

            # else use specific data
            if ledger_type == 'deposit':
                response = KRAKEN_SPECIFIC_DEPOSITS_RESPONSE
            elif ledger_type == 'withdrawal':
                response = KRAKEN_SPECIFIC_WITHDRAWALS_RESPONSE
            else:
                raise AssertionError('Unknown ledger type at kraken ledgers mock query')

            return rlk_jsonloads(response)

        return super().query_private(method, req)


@pytest.fixture(scope='session')
def kraken(session_inquirer, messages_aggregator, session_database):
    mock = MockKraken(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=session_database,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_kraken(inquirer, function_scope_messages_aggregator, database):
    mock = MockKraken(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
