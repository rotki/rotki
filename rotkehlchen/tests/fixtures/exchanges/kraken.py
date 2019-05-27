import base64
import json
import random
from typing import Dict, List, Optional

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import S_EUR, S_USD
from rotkehlchen.fval import FVal
from rotkehlchen.kraken import KRAKEN_ASSETS, KRAKEN_DELISTED, Kraken, world_to_kraken_pair
from rotkehlchen.order_formatting import TradeType
from rotkehlchen.tests.utils.factories import (
    make_random_b64bytes,
    make_random_positive_fval,
    make_random_timestamp,
    make_random_uppercasenumeric_string,
)
from rotkehlchen.typing import Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.serialization import rlk_jsonloads


def get_random_kraken_asset() -> Asset:
    kraken_assets = set(KRAKEN_ASSETS) - set(KRAKEN_DELISTED)
    return random.choice(kraken_assets)


def generate_random_kraken_balance_response():
    kraken_assets = set(KRAKEN_ASSETS) - set(KRAKEN_DELISTED)
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


def generate_random_kraken_ledger_data(
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


class MockKraken(Kraken):

    def first_connection(self):
        if self.first_connection_made:
            return
        # Perhaps mock this too?
        self.tradeable_pairs = self.query_public('AssetPairs')
        self.get_fiat_prices_from_ticker()
        self.first_connection_made = True
        return

    def main_logic(self):
        pass

    def query_private(self, method: str, req: Optional[dict] = None) -> dict:
        self.first_connection()
        if method == 'Balance':
            return generate_random_kraken_balance_response()
        elif method == 'TradesHistory':
            trades_num = random.randint(1, 49)
            start = req['start']
            end = req['end']

            # Trades is a dict with txid as the key
            trades = {}
            for _ in range(trades_num):
                trade = generate_random_kraken_trade_data(
                    list(self.tradeable_pairs.keys()),
                    start,
                    end,
                )
                trades[trade['ordertxid']] = trade

            response_str = json.dumps({'trades': trades, 'count': trades_num})
            return rlk_jsonloads(response_str)
        elif method == 'Ledgers':
            ledgers_num = random.randint(1, 49)
            start = req['start']
            end = req['end']
            ledger_type = req['type']
            # Ledgers is a dict with txid as the key
            ledgers = {}
            for _ in range(ledgers_num):
                ledger = generate_random_kraken_ledger_data(
                    start_ts=start,
                    end_ts=end,
                    ledger_type=ledger_type,
                )
                ledgers[ledger['refid']] = ledger

            response_str = json.dumps({'ledger': ledgers, 'count': ledgers_num})
            return rlk_jsonloads(response_str)

        return super().query_private(method, req)


@pytest.fixture(scope='session')
def kraken(session_data_dir, session_inquirer):
    mock = MockKraken(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        user_directory=session_data_dir,
        msg_aggregator=MessagesAggregator(),
        usd_eur_price=session_inquirer.query_fiat_pair(S_EUR, S_USD),
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_kraken(accounting_data_dir, inquirer):
    mock = MockKraken(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        user_directory=accounting_data_dir,
        msg_aggregator=MessagesAggregator(),
        usd_eur_price=inquirer.query_fiat_pair(S_EUR, S_USD),
    )
    return mock
