import pytest
from web3 import Web3

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.makerdao.vaults import (
    MakerDAOVault,
    MakerDAOVaults,
    get_vault_normalized_balance,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.constants import A_BAT
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.makerdao import VaultTestData, create_web3_mock


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


@pytest.fixture
def use_etherscan() -> bool:
    return False


@pytest.fixture
def makerdao_test_data(
        ethereum_accounts,
        inquirer,  # pylint: disable=unused-argument
) -> VaultTestData:
    user_address = ethereum_accounts[1]
    vault0 = MakerDAOVault(
        identifier=1,
        owner=user_address,
        urn=make_ethereum_address(),
        collateral_type='ETH-A',
        collateral_asset=A_ETH,
        collateral=Balance(FVal('3.1'), FVal('850.1')),
        debt=Balance(FVal('635.1'), FVal('952.65')),
        collateralization_ratio='133.85%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('307.3064516129032258064516129'),
        stability_fee=ZERO,
    )
    vault1 = MakerDAOVault(
        identifier=2,
        owner=user_address,
        urn=make_ethereum_address(),
        collateral_type='BAT-A',
        collateral_asset=A_BAT,
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
        makerdao_vaults = MakerDAOVaults(
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
def test_get_vault_normalized_balance(
        inquirer,  # pylint: disable=unused-argument
        mocked_current_prices,
):
    debt_value = FVal('2000')
    vault = MakerDAOVault(
        identifier=1,
        collateral_type='ETH-A',
        collateral_asset=A_ETH,
        owner=make_ethereum_address(),
        collateral=Balance(FVal('100'), FVal('20000')),
        debt=Balance(debt_value, debt_value * mocked_current_prices['DAI']),
        collateralization_ratio='990%',
        liquidation_ratio=FVal(1.5),
        liquidation_price=FVal('50'),  # not calculated to be correct
        urn=make_ethereum_address(),
        stability_fee=ZERO,
    )
    expected_result = Balance(amount=FVal('89.9'), usd_value=FVal('17980'))
    assert get_vault_normalized_balance(vault) == expected_result
