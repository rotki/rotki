import random
from typing import Optional

import pytest

from rotkehlchen.kraken import KRAKEN_TO_WORLD, Kraken
from rotkehlchen.tests.utils.factories import (
    make_random_bytes_for_requests,
    make_random_positive_fval,
)


def generate_random_kraken_balance_response():
    kraken_assets = KRAKEN_TO_WORLD.keys()
    number_of_assets = random.randrange(0, len(kraken_assets))
    chosen_assets = random.sample(kraken_assets, number_of_assets)

    balances = {}
    for asset in chosen_assets:
        balances[asset] = make_random_positive_fval()

    return balances


class MockKraken(Kraken):

    def first_connection(self):
        # Perhaps mock this too?
        self.tradeable_pairs = self.query_public('AssetPairs')
        self.ticker = {}
        self.ticker['XXBTZEUR'] = {'c': [make_random_positive_fval()]}
        self.ticker['XXBTZUSD'] = {'c': [make_random_positive_fval()]}
        self.ticker['XETHZEUR'] = {'c': [make_random_positive_fval()]}
        self.ticker['XETHZUSD'] = {'c': [make_random_positive_fval()]}
        self.ticker['XREPZEUR'] = {'c': [make_random_positive_fval()]}
        self.ticker['XXMRZEUR'] = {'c': [make_random_positive_fval()]}
        self.ticker['XXMRZUSD'] = {'c': [make_random_positive_fval()]}
        self.ticker['XETCZEUR'] = {'c': [make_random_positive_fval()]}
        self.ticker['XETCZUSD'] = {'c': [make_random_positive_fval()]}

        self.calculate_fiat_prices_from_ticker()
        return

    def main_logic(self):
        pass

    def query_private(self, method: str, req: Optional[dict] = None) -> dict:
        if method == 'Balance':
            return generate_random_kraken_balance_response()

        return super().query_private(method, req)


@pytest.fixture
def kraken(tmpdir):
    mock = MockKraken(
        api_key=make_random_bytes_for_requests(128),
        secret=make_random_bytes_for_requests(128),
        data_dir=tmpdir
    )
    return mock
