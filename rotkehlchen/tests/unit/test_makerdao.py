from collections import defaultdict
from contextlib import ExitStack, nullcontext

import pytest
from web3 import Web3

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.makerdao.cache import (
    ilk_cache_foreach,
    query_ilk_registry_and_maybe_update_cache,
)
from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_VAULT
from rotkehlchen.chain.ethereum.modules.makerdao.vaults import MakerdaoVault, MakerdaoVaults
from rotkehlchen.chain.evm.types import Web3Node
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BAT, A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.migrations.manager import (
    MIGRATIONS_LIST,
    maybe_apply_globaldb_migrations,
)
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.blockchain import (
    get_web3_node_from_inquirer,
    set_web3_node_in_inquirer,
)
from rotkehlchen.tests.utils.constants import A_GNO
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_migrations
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
        urn=make_evm_address(),
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
        urn=make_evm_address(),
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
    proxy_address = make_evm_address()
    return VaultTestData(
        vaults=expected_vaults,
        proxy_mappings={user_address: proxy_address},
        mock_contracts=['GetCDPS', 'ProxyRegistry', 'VAT', 'SPOT', 'JUG'],
    )


@pytest.fixture(name='makerdao_vaults')
def fixture_makerdao_vaults(
        ethereum_inquirer,
        database,
        function_scope_messages_aggregator,
        use_etherscan,
        start_with_valid_premium,
        rotki_premium_credentials,
        makerdao_test_data,
        username,
):
    if not use_etherscan:
        set_web3_node_in_inquirer(
            ethereum_inquirer=ethereum_inquirer,
            web3node=Web3Node(web3_instance=Web3(), is_pruned=False, is_archive=True),
        )
        web3_node = get_web3_node_from_inquirer(ethereum_inquirer)
        web3_patch = create_web3_mock(web3=web3_node.web3_instance, ethereum=ethereum_inquirer, test_data=makerdao_test_data)  # noqa: E501
    else:
        web3_patch = nullcontext()

    premium = None
    if start_with_valid_premium:
        premium = Premium(credentials=rotki_premium_credentials, username=username)

    with web3_patch:
        return MakerdaoVaults(
            ethereum_inquirer=ethereum_inquirer,
            database=database,
            premium=premium,
            msg_aggregator=function_scope_messages_aggregator,
        )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('mocked_proxies', [{}])
def test_get_vaults(makerdao_vaults, makerdao_test_data, ethereum_inquirer):
    web3_node = get_web3_node_from_inquirer(makerdao_vaults.ethereum)
    web3_patch = create_web3_mock(web3=web3_node.web3_instance, ethereum=ethereum_inquirer, test_data=makerdao_test_data)  # noqa: E501
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
    owner = make_evm_address()
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
        urn=make_evm_address(),
        stability_fee=ZERO,
    )
    expected_result = BalanceSheet(
        assets=defaultdict(Balance, {A_ETH: {CPT_VAULT: Balance(FVal('100'), FVal('20000'))}}),
        liabilities=defaultdict(Balance, {A_DAI: {CPT_VAULT: Balance(FVal('2000'), FVal('2020'))}}),  # noqa: E501
    )
    assert vault.get_balance() == expected_result


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('globaldb_upgrades', [[]])
@pytest.mark.parametrize('run_globaldb_migrations', [False])
@pytest.mark.parametrize('custom_globaldb', ['v4_global_before_migration1.db'])
def test_query_ilk_registry_and_update_cache(globaldb, ethereum_inquirer):
    """Test at the state of the global DB going from 1.27.0 to 1.27.1 when ilk cache is introduced

    - Apply the migration so the ilk registry abi is there
    - Query the ilk registry and populate the ilk cache
    - Test that all went fine and that all new data is in the DB

    This also tests that ilk_cache_foreach works properly and iterates everything in the DB
    """
    with ExitStack() as stack:
        patch_for_globaldb_migrations(stack, [MIGRATIONS_LIST[0]])
        maybe_apply_globaldb_migrations(globaldb.conn)

    query_ilk_registry_and_maybe_update_cache(ethereum_inquirer)

    def assert_new_join_collateral(
            asset: Asset,
            join_address: str,
            expected_identifier: str,
            expected_join_address: str,
            expected_abi_entry: tuple[str, str],
    ) -> None:
        assert asset.identifier == expected_identifier
        assert join_address == expected_join_address
        contract = ethereum_inquirer.contracts.contract_by_address(join_address)
        assert contract.address == expected_join_address
        for entry in contract.abi:
            if entry['type'] == expected_abi_entry[0] and entry['name'] == expected_abi_entry[1]:
                break
        else:
            raise AssertionError(
                f'abi should have an {expected_abi_entry[0]} entry with '
                f'name {expected_abi_entry[1]}',
            )

    count = 0
    got_gno = got_reth = got_wsteth = got_crv = got_comp = False
    with globaldb.conn.read_ctx() as cursor:
        for ilk, ilk_class, asset, join_address in ilk_cache_foreach(cursor):
            assert ilk_class in range(1, 5)
            count += 1
            # check some known ones
            if ilk == 'ETH-A':
                assert asset == A_ETH
                assert join_address == '0x2F0b23f53734252Bda2277357e97e1517d6B042A'
                assert ilk_class == 1
            elif ilk == 'USDC-B':
                assert asset == A_USDC
                assert join_address == '0x2600004fd1585f7270756DDc88aD9cfA10dD0428'
                assert ilk_class == 1
            elif ilk == 'GNO-A':  # was not in 1.27
                assert_new_join_collateral(asset, join_address, A_GNO.identifier, '0x7bD3f01e24E0f0838788bC8f573CEA43A80CaBB5', ('event', 'LogNote'))  # noqa: E501
                got_gno = True
                assert ilk_class == 1
            elif ilk == 'RETH-A':  # was not in 1.27
                assert_new_join_collateral(asset, join_address, 'eip155:1/erc20:0xae78736Cd615f374D3085123A210448E74Fc6393', '0xC6424e862f1462281B0a5FAc078e4b63006bDEBF', ('event', 'LogNote'))  # noqa: E501
                got_reth = True
                assert ilk_class == 1
            elif ilk == 'WSTETH-A':  # was not in 1.27
                assert_new_join_collateral(asset, join_address, 'eip155:1/erc20:0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0', '0x10CD5fbe1b404B7E19Ef964B63939907bdaf42E2', ('event', 'LogNote'))  # noqa: E501
                got_wsteth = True
                assert ilk_class == 1
            elif ilk == 'CRVV1ETHSTETH-A':  # not in 1.27 but has cropjoin adapter via proxy
                assert_new_join_collateral(asset, join_address, 'eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E', '0x82D8bfDB61404C796385f251654F6d7e92092b5D', ('function', 'implementation'))  # noqa: E501
                got_crv = True
                assert ilk_class == 1
            elif ilk == 'DIRECT-COMPV2-DAI':  # not in 1.27 but has D3MHub adapter
                assert_new_join_collateral(asset, join_address, 'eip155:1/erc20:0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643', '0x12F36cdEA3A28C35aC8C6Cc71D9265c17C74A27F', ('event', 'Exit'))  # noqa: E501
                got_comp = True
                assert ilk_class == 4

        assert count == 60
        assert got_gno == got_wsteth == got_reth == got_crv == got_comp is True
