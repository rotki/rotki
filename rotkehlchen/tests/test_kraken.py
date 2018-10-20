from rotkehlchen.kraken import KRAKEN_TO_WORLD, WORLD_TO_KRAKEN


def test_querying_balances(kraken):
    result, error_or_empty = kraken.query_balances()
    assert error_or_empty == ''
    assert isinstance(result, dict)
    for name, entry in result.items():
        assert name in WORLD_TO_KRAKEN
        assert 'usd_value' in entry
        assert 'amount' in entry


def test_coverage_of_kraken_balances(kraken):
    our_known_assets = set(KRAKEN_TO_WORLD.keys())
    all_assets = set(kraken.query_public('Assets').keys())

    diff = our_known_assets.symmetric_difference(all_assets)
    assert len(diff) == 0, (
        f"Our known assets don't match kraken's assets. Difference: {diff}"
    )
