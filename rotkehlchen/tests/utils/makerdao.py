import types
from typing import TYPE_CHECKING, Any, NamedTuple
from unittest.mock import _patch, patch

from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.modules.makerdao.constants import WAD
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.tests.utils.factories import ZERO_ETH_ADDRESS

if TYPE_CHECKING:
    from web3 import Web3

    from rotkehlchen.chain.ethereum.modules.makerdao.vaults import MakerdaoVault
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import ChecksumEvmAddress


class VaultTestData(NamedTuple):
    vaults: list[MakerdaoVault]
    proxy_mappings: dict[ChecksumEvmAddress, ChecksumEvmAddress]
    mock_contracts: list[str]


class MockCaller:
    def __init__(self, test_data: VaultTestData, **kwargs: Any) -> None:
        self.test_data = test_data
        for attr, value in kwargs.items():
            # Set the callable given from kwarg as a bound class method
            setattr(self, attr, types.MethodType(value, self))


class MockContract:
    def __init__(self, test_data: VaultTestData, **kwargs: Any) -> None:
        self.caller = MockCaller(test_data, **kwargs)


def mock_get_cdps_asc(
        self: MockCaller,
        cdp_manager_address: Any,  # pylint: disable=unused-argument
        proxy: Any,  # pylint: disable=unused-argument
) -> list[list[Any]]:
    result: list[list[Any]] = [[], [], []]
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


def mock_registry_proxies(
        self: MockCaller,
        address: ChecksumEvmAddress,
) -> ChecksumEvmAddress:
    return self.test_data.proxy_mappings.get(address, ZERO_ETH_ADDRESS)


def mock_vat_urns(
        self: MockCaller,
        ilk: Any,  # pylint: disable=unused-argument
        urn: ChecksumEvmAddress,
) -> tuple[FVal, FVal]:
    for vault in self.test_data.vaults:
        if vault.urn == urn:
            result_a = vault.collateral.amount * WAD
            rate = 100
            result_b = ((vault.debt.amount * RAY) / rate) * WAD
            return result_a, result_b

    raise AssertionError(f'Could not find a mock for vat urns for urn {urn}')


def mock_vat_ilks(self: MockCaller, ilk: Any) -> tuple[int, int, FVal]:
    for vault in self.test_data.vaults:
        vault_ilk = bytearray(vault.collateral_type.encode())
        vault_ilk.extend(
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        )
        if vault_ilk == ilk:
            rate = 100
            price = vault.collateral.value / vault.collateral.amount
            spot = (price / vault.liquidation_ratio) * RAY
            whatever = 1
            return whatever, rate, spot

    raise AssertionError(f'Could not find a mock for vat ilks for ilk {ilk}')


def mock_spot_ilks(self: MockCaller, ilk: Any) -> tuple[int, FVal]:
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


def mock_jug_ilks(_: MockCaller, ilk: Any) -> tuple[int, int]:
    if 'ETH-A' in str(ilk):
        duty = 1000000000000000000000000000  # 0%
    elif 'BAT-A' in str(ilk):
        duty = 1000000000236936036262880196  # 0.75%
    else:
        raise AssertionError(f'Unexpected ilk {ilk!s} in unit tests')

    whatever = 1
    return duty, whatever


def create_web3_mock(
        web3: Web3,
        ethereum: EthereumInquirer,
        test_data: VaultTestData,
) -> _patch:
    def mock_contract(
            address: ChecksumEvmAddress,
            abi: Any,
    ) -> MockContract:  # pylint: disable=unused-argument
        mock_proxy_registry = (
            address == string_to_evm_address('0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4') and
            'ProxyRegistry' in test_data.mock_contracts
        )
        if address == string_to_evm_address('0x36a724Bd100c39f0Ea4D3A20F7097eE01A8Ff573') and 'GetCDPS' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, getCdpsAsc=mock_get_cdps_asc)
        if mock_proxy_registry:
            return MockContract(test_data, proxies=mock_registry_proxies)
        if address == string_to_evm_address('0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B') and 'VAT' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, urns=mock_vat_urns, ilks=mock_vat_ilks)
        if address == string_to_evm_address('0x65C79fcB50Ca1594B025960e539eD7A9a6D434A3') and 'SPOT' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, ilks=mock_spot_ilks)
        if address == string_to_evm_address('0x19c0976f590D67707E62397C87829d896Dc0f1F1') and 'JUG' in test_data.mock_contracts:  # noqa: E501
            return MockContract(test_data, ilks=mock_jug_ilks)

        raise AssertionError('Got unexpected address for contract during tests')

    return patch.object(
        web3.eth,
        'contract',
        side_effect=mock_contract,
    )
