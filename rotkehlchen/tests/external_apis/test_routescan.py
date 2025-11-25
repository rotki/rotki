import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.externalapis.routescan import ROUTESCAN_SUPPORTED_CHAINS, Routescan
from rotkehlchen.types import ChainID


@pytest.fixture(name='routescan')
def fixture_routescan(database, messages_aggregator):
    return Routescan(
        database=database,
        msg_aggregator=messages_aggregator,
    )


def test_routescan_url_formatting(routescan: Routescan) -> None:
    formatted_url = routescan._get_url(chain_id=ChainID.ETHEREUM)
    assert formatted_url == 'https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api'

    formatted_url = routescan._get_url(chain_id=ChainID.OPTIMISM)
    assert formatted_url == 'https://api.routescan.io/v2/network/mainnet/evm/10/etherscan/api'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_routescan_has_activity(routescan: Routescan) -> None:
    for chain in ROUTESCAN_SUPPORTED_CHAINS:
        assert routescan.has_activity(
            chain_id=chain,
            account=string_to_evm_address('0x56a1A34F0d33788ebA53e2706854A37A5F275536'),
        ) == HasChainActivity.TRANSACTIONS  # nicholasyoder.eth - has txs in all chains supported by routescan  # noqa: E501
        assert routescan.has_activity(
            chain_id=chain,
            account=string_to_evm_address('0x84e8EE8911c147755bD70084b6b4D1a5A8351476'),
        ) == HasChainActivity.NONE  # random address with no activity
