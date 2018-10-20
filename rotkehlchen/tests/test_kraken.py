from rotkehlchen.kraken import KRAKEN_TO_WORLD


def test_foo(kraken):
    kraken.query_balances()


def test_coverage_of_kraken_balances(kraken):
    our_known_assets = set(KRAKEN_TO_WORLD.keys())
    all_assets = set(kraken.query_public('Assets').keys())

    diff = our_known_assets.symmetric_difference(all_assets)
    assert len(diff) == 0, (
        f"Our known assets don't match kraken's assets. Difference: {diff}"
    )
