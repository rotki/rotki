from collections import defaultdict

import pytest
from web3 import Web3

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import (
    GEMJOIN_MAPPING,
    MakerdaoVault,
    MakerdaoVaults,
    const_collateral_type_mapping,
)
from rotkehlchen.constants.assets import A_BAT, A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.makerdao import VaultTestData, create_web3_mock


def assert_vaults_equal(a: MakerdaoVault, b: MakerdaoVault) -> None:
    attrs = [
        x for x in MakerdaoVault.__dict__ if
        not x.startswith('_') and not callable(getattr(MakerdaoVault, x))
    ]
    for attr in attrs:
        vala = getattr(a, attr)
        valb = getattr(b, attr)
        msg = f'Vaults differ in attribute "{attr}". "{vala}" != "{valb}"'
        if isinstance(vala, FVal):
            assert vala.is_close(valb), msg
        else:
            assert vala == valb, msg


@pytest.fixture(name='use_etherscan')
def fixture_use_etherscan() -> bool:
    return False


@pytest.fixture(name='makerdao_test_data')
def fixture_makerdao_test_data(
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
) -> VaultTestData:
    user_address = ethereum_accounts[1]
    vault0 = MakerdaoVault(
        identifier=1,
        owner=user_address,
        urn=make_ethereum_address(),
        collateral_type='ETH-A',
        collateral_asset=A_ETH.resolve_to_crypto_asset(),
        collateral=Balance(FVal('3.1'), FVal('850.1')),
        debt=Balance(FVal('635.1'), FVal('952.65')),
        collateralization_ratio='133.85%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('307.3064516129032258064516129'),
        stability_fee=ZERO,
    )
    vault1 = MakerdaoVault(
        identifier=2,
        owner=user_address,
        urn=make_ethereum_address(),
        collateral_type='BAT-A',
        collateral_asset=A_BAT.resolve_to_crypto_asset(),
        collateral=Balance(FVal('255.1'), FVal('0.09055272442179537436299490395')),
        debt=Balance(FVal('15.4'), FVal('23.1')),
        collateralization_ratio='0.59%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('0.09055272442179537436299490396'),
        stability_fee=FVal('0.0075'),
    )
    expected_vaults = [vault0, vault1]
    proxy_address = make_ethereum_address()
    return VaultTestData(
        vaults=expected_vaults,
        proxy_mappings={user_address: proxy_address},
        mock_contracts=['GetCDPS', 'ProxyRegistry', 'VAT', 'SPOT', 'JUG'],
    )


@pytest.fixture(name='makerdao_vaults')
def fixture_makerdao_vaults(
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
        makerdao_vaults = MakerdaoVaults(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=function_scope_messages_aggregator,
        )
    return makerdao_vaults


@pytest.mark.parametrize('number_of_eth_accounts', [2])
def test_get_vaults(makerdao_vaults, makerdao_test_data):
    web3_patch = create_web3_mock(web3=makerdao_vaults.ethereum.web3, test_data=makerdao_test_data)
    with web3_patch:
        vaults = makerdao_vaults.get_vaults()

    for idx, vault in enumerate(vaults):
        assert_vaults_equal(vault, makerdao_test_data.vaults[idx])


@pytest.mark.parametrize('mocked_current_prices', [{
    'ETH': FVal('200'),
    'DAI': FVal('1.01'),
}])
def test_get_vault_balance(
        inquirer,  # pylint: disable=unused-argument
        mocked_current_prices,
):
    debt_value = FVal('2000')
    owner = make_ethereum_address()
    vault = MakerdaoVault(
        identifier=1,
        collateral_type='ETH-A',
        collateral_asset=A_ETH,
        owner=owner,
        collateral=Balance(FVal('100'), FVal('20000')),
        debt=Balance(debt_value, debt_value * mocked_current_prices['DAI']),
        collateralization_ratio='990%',
        liquidation_ratio=FVal(1.5),
        liquidation_price=FVal('50'),  # not calculated to be correct
        urn=make_ethereum_address(),
        stability_fee=ZERO,
    )
    expected_result = BalanceSheet(
        assets=defaultdict(Balance, {A_ETH: Balance(FVal('100'), FVal('20000'))}),
        liabilities=defaultdict(Balance, {A_DAI: Balance(FVal('2000'), FVal('2020'))}),
    )
    assert vault.get_balance() == expected_result


def test_vault_types():
    collateral_type_mapping = const_collateral_type_mapping()
    assert len(collateral_type_mapping) == len(GEMJOIN_MAPPING)
    assert set(collateral_type_mapping.keys()) == set(GEMJOIN_MAPPING.keys())
    for collateral_type, asset in collateral_type_mapping.items():
        if collateral_type == 'PAXUSD-A':
            assert asset.identifier == ethaddress_to_identifier('0x8E870D67F660D95d5be530380D0eC0bd388289E1')  # PAX # noqa: E501
            continue

        assert asset.symbol.lower() == collateral_type.split('-')[0].lower()
