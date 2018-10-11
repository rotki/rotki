import random
from typing import Optional

import pytest

from rotkehlchen.kraken import KRAKEN_TO_WORLD, Kraken
from rotkehlchen.tests.utils.factories import make_random_bytes, make_random_positive_fval


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
        import pdb
        pdb.set_trace()
        return

    def query_private(self, method: str, req: Optional[dict] = None) -> dict:
        if method == 'Balance':
            return generate_random_kraken_balance_response()

        return super().query_private(method, req)


@pytest.fixture
def kraken(tmpdir):
    mock = MockKraken(
        api_key=make_random_bytes(256),
        secret=make_random_bytes(256),
        data_dir=tmpdir
    )
    return mock
