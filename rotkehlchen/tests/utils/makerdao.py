import types
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import patch

from web3 import Web3

from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.modules.makerdao.constants import WAD
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import MakerdaoVault
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import ZERO_ETH_ADDRESS
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


class VaultTestData(NamedTuple):
    vaults: list[MakerdaoVault]
    proxy_mappings: dict[ChecksumEvmAddress, ChecksumEvmAddress]
    mock_contracts: list[str]


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
) -> list[list]:
    result: list[list] = [[], [], []]
    for entry in self.test_data.vaults:
        result[0].append(entry.identifier)
        result[1].append(entry.urn)
        ilk = bytearray(entry.collateral_type.encode())
        ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        result[2].append(bytes(ilk))

    return result


def mock_registry_proxies(self, address) -> ChecksumEvmAddress:
    return self.test_data.proxy_mappings.get(address, ZERO_ETH_ADDRESS)


def mock_vat_urns(
        self,
        ilk,  # pylint: disable=unused-argument
        urn,
) -> tuple[FVal, FVal]:
    for vault in self.test_data.vaults:
        if vault.urn == urn:
            result_a = vault.collateral.amount * WAD
            rate = 100
            result_b = ((vault.debt.amount * RAY) / rate) * WAD
            return result_a, result_b

    raise AssertionError(f'Could not find a mock for vat urns for urn {urn}')


def mock_vat_ilks(self, ilk) -> tuple[int, int, FVal]:
    for vault in self.test_data.vaults:
        vault_ilk = bytearray(vault.collateral_type.encode())
        vault_ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        if vault_ilk == ilk:
            rate = 100
            price = vault.collateral.usd_value / vault.collateral.amount
            spot = (price / vault.liquidation_ratio) * RAY
            whatever = 1
            return whatever, rate, spot

    raise AssertionError(f'Could not find a mock for vat ilks for ilk {ilk}')


def mock_spot_ilks(self, ilk) -> tuple[int, FVal]:
    for vault in self.test_data.vaults:
        vault_ilk = bytearray(vault.collateral_type.encode())
        vault_ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        if vault_ilk == ilk:
            whatever = 1
            mat = vault.liquidation_ratio * RAY
            return whatever, mat

    raise AssertionError(f'Could not find a mock for spot ilks for ilk {ilk}')


def mock_jug_ilks(_, ilk) -> tuple[int, int]:
    if 'ETH-A' in str(ilk):
        duty = 1000000000000000000000000000  # 0%
    elif 'BAT-A' in str(ilk):
        duty = 1000000000236936036262880196  # 0.75%
    else:
        raise AssertionError(f'Unexpected ilk {str(ilk)} in unit tests')

    whatever = 1
    return duty, whatever


def create_web3_mock(web3: Web3, ethereum: 'EthereumInquirer', test_data: VaultTestData):
    def mock_contract(address, abi):  # pylint: disable=unused-argument
        mock_proxy_registry = (
            address == ethereum.contracts.contract('DS_PROXY_REGISTRY').address and
            'ProxyRegistry' in test_data.mock_contracts
        )
        if address == ethereum.contracts.contract('MAKERDAO_GET_CDPS').address and 'GetCDPS' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, getCdpsAsc=mock_get_cdps_asc)
        if mock_proxy_registry:
            return MockContract(test_data, proxies=mock_registry_proxies)
        if address == ethereum.contracts.contract('MAKERDAO_VAT').address and 'VAT' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, urns=mock_vat_urns, ilks=mock_vat_ilks)
        if address == ethereum.contracts.contract('MAKERDAO_SPOT').address and 'SPOT' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, ilks=mock_spot_ilks)
        if address == ethereum.contracts.contract('MAKERDAO_JUG').address and 'JUG' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, ilks=mock_jug_ilks)

        raise AssertionError('Got unexpected address for contract during tests')

    return patch.object(
        web3.eth,
        'contract',
        side_effect=mock_contract,
    )
