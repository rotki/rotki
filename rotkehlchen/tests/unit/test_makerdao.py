import types
from typing import Dict, List, NamedTuple, Tuple
from unittest.mock import patch

import pytest
from web3 import Web3

from rotkehlchen.chain.ethereum.makerdao import RAY, WAD, MakerDAO, MakerDAOVault
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.ethereum import (
    MAKERDAO_GET_CDPS,
    MAKERDAO_PROXY_REGISTRY,
    MAKERDAO_SPOT,
    MAKERDAO_VAT,
)
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.constants import A_BAT
from rotkehlchen.tests.utils.factories import ZERO_ETH_ADDRESS, make_ethereum_address
from rotkehlchen.typing import ChecksumEthAddress


def assert_vaults_equal(a: MakerDAOVault, b: MakerDAOVault) -> None:
    attrs = [
        x for x in MakerDAOVault.__dict__ if
        not x.startswith('_') and not callable(getattr(MakerDAOVault, x))
    ]
    for attr in attrs:
        vala = getattr(a, attr)
        valb = getattr(b, attr)
        msg = f'Vaults differ in attribute "{attr}". "{vala}" != "{valb}"'
        if isinstance(vala, FVal):
            assert vala.is_close(valb), msg
        else:
            assert vala == valb, msg


class VaultTestData(NamedTuple):
    vaults: List[MakerDAOVault]
    proxy_mappings: Dict[ChecksumEthAddress, ChecksumEthAddress]


class MockCaller:
    def __init__(self, test_data: VaultTestData, **kwargs) -> None:
        self.test_data = test_data
        for attr, value in kwargs.items():
            # Set the callable given from kwarg as a bound class method
            setattr(self, attr, types.MethodType(value, self))


class MockContract:
    def __init__(self, test_data, **kwargs):
        self.caller = MockCaller(test_data, **kwargs)


def mock_get_cdps_asc(
        self,
        cdp_manager_address,  # pylint: disable=unused-argument
        proxy,  # pylint: disable=unused-argument
) -> List[List]:
    result: List[List] = [[], [], []]
    for entry in self.test_data.vaults:
        result[0].append(entry.identifier)
        result[1].append(entry.urn)
        ilk = bytearray(entry.name.encode())
        ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        result[2].append(ilk)

    return result


def mock_registry_proxies(self, address) -> ChecksumEthAddress:
    return self.test_data.proxy_mappings.get(address, ZERO_ETH_ADDRESS)


def mock_vat_urns(
        self,
        ilk,  # pylint: disable=unused-argument
        urn,
) -> Tuple[FVal, FVal]:
    for vault in self.test_data.vaults:
        if vault.urn == urn:
            result_a = vault.collateral_amount * WAD
            rate = 100
            result_b = ((vault.debt_value * RAY) / rate) * WAD
            return result_a, result_b

    raise AssertionError(f'Could not find a mock for vat urns for urn {urn}')


def mock_vat_ilks(self, ilk) -> Tuple[int, int, FVal]:
    for vault in self.test_data.vaults:
        vault_ilk = bytearray(vault.name.encode())
        vault_ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        if vault_ilk == ilk:
            rate = 100
            price = vault.collateral_usd_value / vault.collateral_amount
            spot = (price / vault.liquidation_ratio) * RAY
            whatever = 1
            return whatever, rate, spot

    raise AssertionError(f'Could not find a mock for vat ilks for ilk {ilk}')


def mock_spot_ilks(self, ilk) -> Tuple[int, FVal]:
    for vault in self.test_data.vaults:
        vault_ilk = bytearray(vault.name.encode())
        vault_ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        if vault_ilk == ilk:
            whatever = 1
            mat = vault.liquidation_ratio * RAY
            return whatever, mat

    raise AssertionError(f'Could not find a mock for spot ilks for ilk {ilk}')


def create_web3_mock(web3: Web3, test_data: VaultTestData):
    def mock_contract(address, abi):  # pylint: disable=unused-argument
        if address == MAKERDAO_GET_CDPS.address:
            return MockContract(test_data, getCdpsAsc=mock_get_cdps_asc)
        elif address == MAKERDAO_PROXY_REGISTRY.address:
            return MockContract(test_data, proxies=mock_registry_proxies)
        elif address == MAKERDAO_VAT.address:
            return MockContract(test_data, urns=mock_vat_urns, ilks=mock_vat_ilks)
        elif address == MAKERDAO_SPOT.address:
            return MockContract(test_data, ilks=mock_spot_ilks)
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
def makerdao_test_data(ethereum_accounts) -> VaultTestData:
    vault0 = MakerDAOVault(
        identifier=1,
        urn=make_ethereum_address(),
        name='ETH-A',
        collateral_asset=A_ETH,
        collateral_amount=FVal('3.1'),
        debt_value=FVal('635.1'),
        collateralization_ratio='133.85%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('307.3064516129032258064516129'),
        collateral_usd_value=FVal('850.1'),
    )
    vault1 = MakerDAOVault(
        identifier=2,
        urn=make_ethereum_address(),
        name='BAT-A',
        collateral_asset=A_BAT,
        collateral_amount=FVal('255.1'),
        debt_value=FVal('15.4'),
        collateralization_ratio='0.59%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('0.09055272442179537436299490396'),
        collateral_usd_value=FVal('0.09055272442179537436299490395'),
    )
    expected_vaults = [vault0, vault1]
    user_address = ethereum_accounts[1]
    proxy_address = make_ethereum_address()
    return VaultTestData(vaults=expected_vaults, proxy_mappings={user_address: proxy_address})


@pytest.fixture
def makerdao(
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
        makerdao = MakerDAO(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=function_scope_messages_aggregator,
        )
    return makerdao


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_get_vaults(makerdao, makerdao_test_data):
    web3_patch = create_web3_mock(web3=makerdao.ethereum.web3, test_data=makerdao_test_data)
    with web3_patch:
        vaults = makerdao.get_vaults()

    for idx, vault in enumerate(vaults):
        assert_vaults_equal(vault, makerdao_test_data.vaults[idx])
