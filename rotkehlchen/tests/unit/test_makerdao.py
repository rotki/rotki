import pytest
from web3 import Web3

from rotkehlchen.chain.ethereum.makerdao import MakerDAO, MakerDAOVault
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
def makerdao_test_data(ethereum_accounts) -> VaultTestData:
    user_address = ethereum_accounts[1]
    vault0 = MakerDAOVault(
        identifier=1,
        owner=user_address,
        urn=make_ethereum_address(),
        collateral_type='ETH-A',
        collateral_asset=A_ETH,
        collateral_amount=FVal('3.1'),
        debt_value=FVal('635.1'),
        collateralization_ratio='133.85%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('307.3064516129032258064516129'),
        collateral_usd_value=FVal('850.1'),
        stability_fee=ZERO,
    )
    vault1 = MakerDAOVault(
        identifier=2,
        owner=user_address,
        urn=make_ethereum_address(),
        collateral_type='BAT-A',
        collateral_asset=A_BAT,
        collateral_amount=FVal('255.1'),
        debt_value=FVal('15.4'),
        collateralization_ratio='0.59%',
        liquidation_ratio=FVal('1.5'),
        liquidation_price=FVal('0.09055272442179537436299490396'),
        collateral_usd_value=FVal('0.09055272442179537436299490395'),
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
