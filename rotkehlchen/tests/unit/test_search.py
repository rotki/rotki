import logging
import subprocess  # noqa: S404  # is only used to execute rotki code here


from rotkehlchen.assets.asset import Asset
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.filtering import LevenshteinFilterQuery
from rotkehlchen.db.search_assets import search_assets_levenshtein
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tests.fixtures.globaldb import create_globaldb
from rotkehlchen.types import Price
from rotkehlchen.utils.gevent_compat import joinall, spawn

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def test_search_assets_levenshtein_multiple(globaldb, database):  # pylint: disable=unused-argument
    """Test that parallel access to levenshtein search does not raise any errors"""
    filter_query = LevenshteinFilterQuery.make(substring_search='ETH')

    def do_search():
        search_assets_levenshtein(
            db=database,
            filter_query=filter_query,
            limit=None,
            search_nfts=False,
        )

    greenlets = [
        spawn(do_search),
        spawn(do_search),
        spawn(do_search),
    ]

    joinall(greenlets)
    assert all(x.exception is None for x in greenlets)


def get_identifier_from_stdout(stdout: str) -> str | None:
    """Utility function to extract the identifier from the stdout of a subprocess."""
    for line in stdout.splitlines():
        if line.startswith('Identifier:'):
            return line.split('Identifier: ')[1].strip()

    return None


def test_db_persistence_after_search(messages_aggregator):
    """Test that manual prices of a newly added asset are saved in the global database,
    when doing an asset search before the price is added.
    Issue tested: https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=69334133
    - Add a new custom asset
    - Search for the custom asset
    - Add a manual price for the custom asset
    - Crash the application
    - Check that the manual price is still in the global database"""
    rotki_process = subprocess.Popen(
        [  # noqa: S607  # is only used to execute rotki code here
            'python',
            '-m'
            'rotkehlchen.tests.utils.crash_test',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    rotki_process.wait()
    stdout, stderr = rotki_process.communicate()
    log.info(stdout)
    log.debug(stderr)
    assert (custom_asset_identifier := get_identifier_from_stdout(stdout)) is not None

    globaldb = create_globaldb(
        data_directory=default_data_directory().parent / 'test_data',
        sql_vm_instructions_cb=0,
        messages_aggregator=messages_aggregator,
    )
    assert globaldb.get_manual_current_price(Asset(custom_asset_identifier)) == (A_USD, Price(FVal(123)))  # noqa: E501
    globaldb.delete_asset_by_identifier(custom_asset_identifier)
    globaldb.cleanup()
