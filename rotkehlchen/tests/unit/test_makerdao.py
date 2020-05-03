from typing import Dict, List, NamedTuple
from unittest.mock import patch

import pytest
from web3 import Web3

from rotkehlchen.chain.ethereum.makerdao import MakerDAO, MakerDAOVault
from rotkehlchen.constants.ethereum import (
    MAKERDAO_GET_CDPS_ADDRESS,
    MAKERDAO_PROXY_REGISTRY_ADDRESS,
)
from rotkehlchen.tests.utils.factories import ZERO_ETH_ADDRESS, make_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress


class VaultTestData(NamedTuple):
    vaults: List[MakerDAOVault]
    proxy_mappings: Dict[ChecksumEthAddress, ChecksumEthAddress]


class MockGetCdpsCaller:
    def __init__(self, test_data: VaultTestData) -> None:
        self.test_data = test_data

    def getCdpsAsc(  # noqa: N802
            self,
            cdp_manager_address,  # pylint: disable=unused-argument
            proxy,  # pylint: disable=unused-argument
    ) -> List[List]:
        result: List[List] = [[], [], []]
        for entry in self.test_data.vaults:
            result[0].append(entry.identifier)
            result[1].append(entry.urn)
            ilk = bytearray(entry.ilk.encode())
            ilk.extend(
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            )
            result[2].append(ilk)

        return result


class MockGetCdps:

    def __init__(self, test_data):
        self.caller = MockGetCdpsCaller(test_data)


class MockProxyRegistryCaller:
    def __init__(self, test_data: VaultTestData) -> None:
        self.test_data = test_data

    def proxies(self, address) -> ChecksumEthAddress:
        return self.test_data.proxy_mappings.get(address, ZERO_ETH_ADDRESS)


class MockProxyRegistry:

    def __init__(self, test_data):
        self.caller = MockProxyRegistryCaller(test_data)


def create_web3_mock(web3: Web3, test_data: VaultTestData):
    def mock_contract(address, abi):  # pylint: disable=unused-argument
        if address == MAKERDAO_GET_CDPS_ADDRESS:
            return MockGetCdps(test_data)
        elif address == MAKERDAO_PROXY_REGISTRY_ADDRESS:
            return MockProxyRegistry(test_data)
        else:
            raise AssertionError('Got unexpected address for contract during tests')

    return patch.object(
        web3.eth,
        'contract',
        side_effect=mock_contract,
    )


@pytest.fixture
def use_etherscan() -> bool:
    return False


@pytest.fixture
def makerdao(ethereum_manager, database, function_scope_messages_aggregator, use_etherscan):
    if not use_etherscan:
        ethereum_manager.connected = True
        ethereum_manager.web3 = Web3()

    return MakerDAO(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_get_vaults(makerdao, ethereum_accounts):
    vault0 = MakerDAOVault(identifier=1, urn=make_ethereum_address(), ilk='ETH-A')
    vault1 = MakerDAOVault(identifier=1, urn=make_ethereum_address(), ilk='BAT-A')
    expected_vaults = [vault0, vault1]
    user_address = ethereum_accounts[1]
    proxy_address = make_ethereum_address()
    test_data = VaultTestData(vaults=expected_vaults, proxy_mappings={user_address: proxy_address})

    web3_patch = create_web3_mock(web3=makerdao.ethereum.web3, test_data=test_data)
    with web3_patch:
        vaults = makerdao.get_vaults()

    assert vaults == expected_vaults
