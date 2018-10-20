import base64
import random
from typing import Optional

import pytest

from rotkehlchen.kraken import KRAKEN_TO_WORLD, Kraken
from rotkehlchen.tests.utils.factories import make_random_b64bytes, make_random_positive_fval


def generate_random_kraken_balance_response():
    kraken_assets = list(KRAKEN_TO_WORLD.keys())
    # remove delisted assets
    kraken_assets.remove('XDAO')
    number_of_assets = random.randrange(0, len(kraken_assets))
    chosen_assets = random.sample(kraken_assets, number_of_assets)

    balances = {}
    for asset in chosen_assets:
        balances[asset] = make_random_positive_fval()

    return balances


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
        if method == 'Balance':
            return generate_random_kraken_balance_response()

        return super().query_private(method, req)


@pytest.fixture
def kraken(tmpdir):
    mock = MockKraken(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        data_dir=tmpdir
    )
    return mock
