import pytest
from web3 import Web3

from rotkehlchen.chain.ethereum.aave import Aave
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.makerdao import VaultTestData, create_web3_mock


@pytest.fixture
def makerdao_vaults(
        ethereum_manager,
        database,
        function_scope_messages_aggregator,
        use_etherscan,
        start_with_valid_premium,
        rotki_premium_credentials,
        makerdao_test_data,
):
    if not use_etherscan:
        ethereum_manager.connected = True
        ethereum_manager.web3 = Web3()

    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    web3_patch = create_web3_mock(web3=ethereum_manager.web3, test_data=makerdao_test_data)
    with web3_patch:
        aave = Aave(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=function_scope_messages_aggregator,
        )
    return makerdao_vaults
