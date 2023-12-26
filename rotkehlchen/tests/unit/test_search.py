import gevent

from rotkehlchen.db.filtering import LevenshteinFilterQuery
from rotkehlchen.db.search_assets import search_assets_levenshtein


def test_search_assets_levensthein_multiple(globaldb, database):  # pylint: disable=unused-argument
    """Test that parallel access to levensthein search does not raise any errors"""
    filter_query = LevenshteinFilterQuery.make(substring_search='ETH')

    def do_search():
        search_assets_levenshtein(
            db=database,
            filter_query=filter_query,
            limit=None,
            search_nfts=False,
        )

    greenlets = [
        gevent.spawn(do_search),
        gevent.spawn(do_search),
        gevent.spawn(do_search),
    ]

    gevent.joinall(greenlets)
    assert all(x.exception is None for x in greenlets)
