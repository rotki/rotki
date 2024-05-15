from collections import defaultdict
from functools import wraps
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_ETHERSCAN_NODE
from rotkehlchen.chain.arbitrum_one.modules.gmx.balances import GmxBalances
from rotkehlchen.chain.arbitrum_one.modules.thegraph.balances import (
    ThegraphBalances as ThegraphBalancesArbitrumOne,
)
from rotkehlchen.chain.ethereum.modules.convex.balances import ConvexBalances
from rotkehlchen.chain.ethereum.modules.curve.balances import CurveBalances
from rotkehlchen.chain.ethereum.modules.eigenlayer.balances import EigenlayerBalances
from rotkehlchen.chain.ethereum.modules.octant.balances import OctantBalances
from rotkehlchen.chain.ethereum.modules.thegraph.balances import ThegraphBalances
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.compound.v3.balances import Compoundv3Balances
from rotkehlchen.chain.evm.tokens import TokenBalancesType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.balances import VelodromeBalances
from rotkehlchen.constants.assets import A_CVX, A_GLM, A_GMX, A_GRT, A_GRT_ARB, A_STETH, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.arbitrum_one import get_arbitrum_allthatnode
from rotkehlchen.tests.utils.constants import CURRENT_PRICE_MOCK
from rotkehlchen.tests.utils.ethereum import (
    get_decoded_events_of_transaction,
    wait_until_all_nodes_connected,
)
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    Price,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd289986c25Ae3f4644949e25bC369e9d8e0caeaD']])
def test_curve_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    database = ethereum_transaction_decoder.database
    tx_hex = deserialize_evm_tx_hash('0x5ae70d68241d85feac65c90e4546154e232dba9fecad9036bcec10082acc9d46')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    curve_balances_inquirer = CurveBalances(
        database=database,
        evm_inquirer=ethereum_inquirer,
    )
    curve_balances = curve_balances_inquirer.query_balances()
    user_balance = curve_balances[ethereum_accounts[0]]
    asset = EvmToken('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F')
    assert user_balance.assets[asset] == Balance(
        amount=FVal('7985.261401730774426743'),
        usd_value=FVal('11977.8921025961616401145'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_convex_gauges_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    database = ethereum_transaction_decoder.database
    tx_hex = deserialize_evm_tx_hash('0x0d8863fb26d57ca11dc11c694dbf6a13ef03920e39d0482081aa88b0b20ba61b')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    convex_balances_inquirer = ConvexBalances(
        database=database,
        evm_inquirer=ethereum_inquirer,
    )
    convex_balances = convex_balances_inquirer.query_balances()
    user_balance = convex_balances[ethereum_accounts[0]]
    asset = EvmToken('eip155:1/erc20:0x06325440D014e39736583c165C2963BA99fAf14E')
    assert user_balance.assets[asset] == Balance(
        amount=FVal('2.096616951181033047'),
        usd_value=FVal('3.1449254267715495705'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_convex_staking_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check Convex balance query for CSV locked and staked"""
    database = ethereum_transaction_decoder.database
    tx_hex = deserialize_evm_tx_hash('0x0d8863fb26d57ca11dc11c694dbf6a13ef03920e39d0482081aa88b0b20ba61b')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    tx_hex = deserialize_evm_tx_hash('0x679746961f731819e351f866b33bc2267dfb341e9d0b30ebccd012834ae3ffde')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    convex_balances_inquirer = ConvexBalances(
        database=database,
        evm_inquirer=ethereum_inquirer,
    )
    convex_balances = convex_balances_inquirer.query_balances()
    user_balance = convex_balances[ethereum_accounts[0]]
    # the amount here is the sum of the locked ~44 and the staked tokens ~333
    assert user_balance.assets[A_CVX.resolve_to_evm_token()] == Balance(
        amount=FVal('378.311754894794233025'),
        usd_value=FVal('567.4676323421913495375'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0c3ce74FCB2B93F9244544919572818Dc2AC0641']])
def test_convex_staking_balances_without_gauges(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """
    Check that convex balances are correctly propagated if one account doesn't have gauges
    deposits but has staked CVX. The reason for this test is that staked/locked CVX is added to the
    balances returned from the gauges and those balances before this test were
    not a defaultdict and could lead to a failure.
    """
    database = ethereum_transaction_decoder.database
    tx_hex = deserialize_evm_tx_hash('0x38bd199803e7cb065c809ce07957afc0647a41da4c0610d1209a843d9b045cd6')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    convex_balances_inquirer = ConvexBalances(
        database=database,
        evm_inquirer=ethereum_inquirer,
    )
    convex_balances = convex_balances_inquirer.query_balances()
    user_balance = convex_balances[ethereum_accounts[0]]
    assert user_balance.assets[A_CVX.resolve_to_evm_token()] == Balance(
        amount=FVal('44.126532249621479557'),
        usd_value=FVal('66.1897983744322193355'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_velodrome_v2_staking_balances(
        optimism_inquirer: 'OptimismInquirer',
        optimism_transaction_decoder: 'OptimismTransactionDecoder',
        optimism_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of velodrome v2 gauges are properly queried."""
    database = optimism_transaction_decoder.database
    tx_hex = deserialize_evm_tx_hash('0xed7e13e4941bba33edbbd70c4f48c734629fd67fe4eac43ce1bed3ef8f3da7df')  # transaction that interacts with the gauge address  # noqa: E501
    get_decoded_events_of_transaction(  # decode events that interact with the gauge address
        evm_inquirer=optimism_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    balances_inquirer = VelodromeBalances(
        database=database,
        evm_inquirer=optimism_inquirer,
    )
    balances = balances_inquirer.query_balances()  # queries the gauge balance of the address if the address has interacted with a known gauge  # noqa: E501
    user_balance = balances[optimism_accounts[0]]
    weth_op_lp_token = evm_address_to_identifier(
        address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        token_type=EvmTokenKind.ERC20,
    )
    assert user_balance.assets[Asset(weth_op_lp_token).resolve_to_evm_token()] == Balance(
        amount=FVal('0.043087772070655563'),  # staked in gauge
        usd_value=FVal('0.0646316581059833445'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x72296d54B83491c59236E45F19b6fdE8a2B2771b']])
def test_thegraph_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of GRT currently delegated to indexers are properly detected."""
    tx_hex = deserialize_evm_tx_hash('0x81cdf7a4201d3e89c9f3a8d3ae18e3cb7ae0e06a5cbc514f1e41504b9b263667')  # noqa: E501
    amount = '6626.873960369737'
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    thegraph_balances_inquirer = ThegraphBalances(
        database=ethereum_transaction_decoder.database,
        evm_inquirer=ethereum_inquirer,
    )
    thegraph_balances = thegraph_balances_inquirer.query_balances()
    user_balance = thegraph_balances[ethereum_accounts[0]]
    assert user_balance.assets[A_GRT.resolve_to_evm_token()] == Balance(
        amount=FVal(amount),
        usd_value=FVal(amount) * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xA9728D95567410555557a54EcA320e5E8bEa36a5']])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(get_arbitrum_allthatnode(weight=ONE, owned=True),)])  # noqa: E501
def test_thegraph_balances_arbitrum_one(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_transaction_decoder: 'ArbitrumOneTransactionDecoder',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        arbitrum_one_manager_connect_at_start,
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of GRT currently delegated to indexers are properly detected."""
    wait_until_all_nodes_connected(
        connect_at_start=arbitrum_one_manager_connect_at_start,
        evm_inquirer=arbitrum_one_inquirer,
    )
    amount = FVal('25.607552758075613')
    tx_hex = deserialize_evm_tx_hash('0x3c846f305330969fb0ddb87c5ae411b4e9692f451a7ff3237b6f71020030c7d1')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=arbitrum_one_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    thegraph_balances_inquirer = ThegraphBalancesArbitrumOne(
        database=arbitrum_one_transaction_decoder.database,
        evm_inquirer=arbitrum_one_inquirer,
    )
    thegraph_balances = thegraph_balances_inquirer.query_balances()
    user_balance = thegraph_balances[arbitrum_one_accounts[0]]
    assert user_balance.assets[A_GRT_ARB.resolve_to_evm_token()] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(ARBITRUM_ONE_ETHERSCAN_NODE,)])
def test_thegraph_balances_vested_arbitrum_one(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_transaction_decoder: 'ArbitrumOneTransactionDecoder',
        ethereum_inquirer: 'EthereumInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        arbitrum_one_manager_connect_at_start,
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of GRT currently vested are properly detected."""
    expected_grt_balance = FVal('246914.881548572905')
    # decode the delegation transfer event which has the vested contract address as delegator_l2
    wait_until_all_nodes_connected(
        connect_at_start=arbitrum_one_manager_connect_at_start,
        evm_inquirer=arbitrum_one_inquirer,
    )
    for tx_hash in (
        '0x48321bb00e5c5b67f080991864606dbc493051d20712735a579d7ae31eca3d78',
        '0xed80711e4cb9c428790f0d9b51f79473bf5253d5d03c04d958d411e7fa34a92e',
    ):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            database=arbitrum_one_transaction_decoder.database,
            tx_hash=deserialize_evm_tx_hash(
                tx_hash,
            ),
        )

    def mock_process_staking_events(self, events):
        original_process_staking_events = ThegraphBalances.process_staking_events

        @wraps(original_process_staking_events)
        def wrapper(*args, **kwargs):
            result = original_process_staking_events(self, *args, **kwargs)
            # Sort the result tuples in alphabetical order to keep it same each run
            sorted_result = sorted(result)
            return sorted_result

        return wrapper(events)

    # Patch it to guarantee order of returned list and thus
    # making the test's remote calls deterministic for VCR
    with patch(
        'rotkehlchen.chain.arbitrum_one.modules.thegraph.balances.ThegraphBalances.process_staking_events',
        new=mock_process_staking_events,
    ) as mock_process_staking_events:
        thegraph_balances_inquirer = ThegraphBalancesArbitrumOne(
            database=arbitrum_one_transaction_decoder.database,
            evm_inquirer=arbitrum_one_inquirer,
        )
        thegraph_balances = thegraph_balances_inquirer.query_balances()
    asset = A_GRT_ARB.resolve_to_evm_token()
    assert thegraph_balances[arbitrum_one_accounts[0]].assets[asset] == Balance(
        amount=expected_grt_balance,
        usd_value=expected_grt_balance * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_octant_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of locked GLM in Octant are properly detected"""
    tx_hex = deserialize_evm_tx_hash('0x29944efad254413b5eccdd5f13f14642ab830dbf51d5f2cfc59cf4957f33671a')  # noqa: E501
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    octant_balances_inquirer = OctantBalances(
        database=ethereum_transaction_decoder.database,
        evm_inquirer=ethereum_inquirer,
    )
    octant_balances = octant_balances_inquirer.query_balances()
    user_balance = octant_balances[ethereum_accounts[0]]
    assert user_balance.assets[A_GLM.resolve_to_evm_token()] == Balance(amount=FVal('1000'), usd_value=FVal('1500'))  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x15AcAA0E27b70AfE3D7631cDAf5516BCAbE3bc0F']])
def test_eigenlayer_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'OptimismTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    database = ethereum_transaction_decoder.database
    tx_hex = deserialize_evm_tx_hash('0x89981857ab9f31369f954ae332ffd910e1f3c8efe531efde5f26666316855591')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=ethereum_transaction_decoder.database,
        tx_hash=tx_hex,
    )
    assert len(events) == 2
    balances_inquirer = EigenlayerBalances(
        database=database,
        evm_inquirer=ethereum_inquirer,
    )
    balances = balances_inquirer.query_balances()
    assert balances[ethereum_accounts[0]].assets[A_STETH.resolve_to_evm_token()] == Balance(
        amount=FVal('0.114063122816914142'),
        usd_value=FVal('0.1710946842253712130'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [[
    '0x328fE286b2bE1895959E2601364AfE9DAA22aba3',
    '0x4ebE485C1DF060f6Fc6E3C3b200EBc21Fe11a94D',
]])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(get_arbitrum_allthatnode(weight=ONE, owned=True),)])  # noqa: E501
@pytest.mark.parametrize('mocked_current_prices', [{
    'eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f': FVal(69928),  # wBTC
    'eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1': FVal(1.001),  # dai
    'eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1': FVal(3583.17),  # weth
}])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
def test_gmx_balances(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_transaction_decoder: 'OptimismTransactionDecoder',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """
    Test querying balances for GMX. We use an address with 2 different positions and the other
    one has a single position. There are both shorts and longs in the data.
    """
    for tx_hash in (
        '0x195cdb1bde8da223c7e6216166f7e8b5b79fee6409dde145a8f3e95223ebcc51',  # short btc
        '0x59d136f8d1b366a895ddf4136fb45d62b862e79f4a937f5a9b33ceec47eaf32f',  # long btc
        '0xf14d5a3f3fa4a4c324f95b70db81502f3d7c1910782381ed82f3580da64b093f',  # long eth
    ):
        tx_hex = deserialize_evm_tx_hash(tx_hash)
        get_decoded_events_of_transaction(
            evm_inquirer=arbitrum_one_inquirer,
            database=arbitrum_one_transaction_decoder.database,
            tx_hash=tx_hex,
        )

    balances_inquirer = GmxBalances(
        database=arbitrum_one_transaction_decoder.database,
        evm_inquirer=arbitrum_one_inquirer,
    )

    # we mock the function call for the user positions since the function returns a set and
    # the inconsistency in the order can affect the output of the mocked responses. We do
    # check that the expected output and the actual output match.
    expected_positions = {
        arbitrum_one_accounts[0]: [
            ('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', True),  # noqa: E501
            ('0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f', '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f', True),  # noqa: E501
        ],
        arbitrum_one_accounts[1]: [
            ('0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1', '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f', False),  # noqa: E501
        ],
    }
    actual_positions = balances_inquirer._extract_unique_deposits()
    for addr, positions in expected_positions.items():
        assert set(actual_positions[addr]) == set(positions)

    with patch(
        'rotkehlchen.chain.arbitrum_one.modules.gmx.balances.GmxBalances._extract_unique_deposits',
        return_value=expected_positions,
    ):
        balances = balances_inquirer.query_balances()

    assert balances[arbitrum_one_accounts[0]].assets == {
        Asset('eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'): Balance(
            amount=FVal('0.020625523771241888'),
            usd_value=FVal('73.904758011400794198629853957124'),
        ),
        Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'): Balance(
            amount=FVal('0.00092231'),
            usd_value=FVal('64.495126014300507906764604009528'),
        ),
    }
    assert balances[arbitrum_one_accounts[1]].assets == {
        Asset('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'): Balance(
            amount=FVal('42.896760410410693074'),
            usd_value=FVal('42.939657170821103766867050208907'),
        ),
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3D3db31AdbCCB6a4e5aE94ec0701d361E147FA6A']])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(get_arbitrum_allthatnode(weight=ONE, owned=True),)])  # noqa: E501
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_gmx_balances_staking(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_transaction_decoder: 'OptimismTransactionDecoder',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        arbitrum_one_manager_connect_at_start,
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Test the balance query for staked GMX. It adds a staking event and then queries the
    balances for that address.
    """
    wait_until_all_nodes_connected(
        connect_at_start=arbitrum_one_manager_connect_at_start,
        evm_inquirer=arbitrum_one_inquirer,
    )
    get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=arbitrum_one_transaction_decoder.database,
        tx_hash=deserialize_evm_tx_hash('0x25160bf17e5a77935c7661933c045739dba44606859a20f00f187ef291e56a8f'),
    )
    balances_inquirer = GmxBalances(
        database=arbitrum_one_transaction_decoder.database,
        evm_inquirer=arbitrum_one_inquirer,
    )
    balances = balances_inquirer.query_balances()
    assert balances[arbitrum_one_accounts[0]].assets == {
        A_GMX: Balance(
            amount=FVal('4.201981641893733976'),
            usd_value=FVal('164.46556146372074782064'),
        ),
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xecdED8b1c603cF21299835f1DFBE37f10F2a29Af', '0x8Cbac427B6967d5d84Ec4230081e2763AB3A8C92',
]])
def test_aave_v3_balances(blockchain: 'ChainsAggregator') -> None:
    """Check that ethereum mainnet Aave v3 positions/liabilities are properly returned in the balances query"""  # noqa: E501
    ethereum_manager = blockchain.get_evm_manager(chain_id=ChainID.ETHEREUM)
    a_eth_usdc = get_or_create_evm_token(
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='aEthUSDC',
        protocol=CPT_AAVE_V3,
    )
    stable_debt_eth_usdc = get_or_create_evm_token(
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0xB0fe3D292f4bd50De902Ba5bDF120Ad66E9d7a39'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='stableDebtEthUSDC',
        protocol=CPT_AAVE_V3,
    )
    variable_debt_eth_usdc = get_or_create_evm_token(
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='variableDebtEthUSDC',
        protocol=CPT_AAVE_V3,
    )

    aave_prices = {
        a_eth_usdc: Price(FVal(0.1)),
        stable_debt_eth_usdc: Price(FVal(10)),
        variable_debt_eth_usdc: Price(FVal(100)),
    }

    def mock_new_balances(addresses: 'Sequence[ChecksumEvmAddress]') -> TokenBalancesType:
        return {
            addresses[0]: {a_eth_usdc: FVal(123), stable_debt_eth_usdc: FVal(456)},
            addresses[1]: {stable_debt_eth_usdc: FVal(456), variable_debt_eth_usdc: FVal(789)},
        }, aave_prices

    balances: defaultdict['ChecksumEvmAddress', 'BalanceSheet'] = defaultdict(BalanceSheet)
    with patch.object(
        target=ethereum_manager.tokens,
        attribute='query_tokens_for_addresses',
        new=mock_new_balances,
    ):
        blockchain.query_evm_tokens(manager=ethereum_manager, balances=balances)

    assert balances == {  # Debt Tokens are moved to liabilities section
        blockchain.accounts.eth[0]: BalanceSheet(
            assets=defaultdict(Balance, {
                a_eth_usdc: Balance(
                    amount=FVal(123),
                    usd_value=FVal(123) * aave_prices[a_eth_usdc],
                ),
            }),
            liabilities=defaultdict(Balance, {
                stable_debt_eth_usdc: Balance(
                    amount=FVal(456),
                    usd_value=FVal(456) * aave_prices[stable_debt_eth_usdc],
                ),
            }),
        ),
        blockchain.accounts.eth[1]: BalanceSheet(
            liabilities=defaultdict(Balance, {
                stable_debt_eth_usdc: Balance(
                    amount=FVal(456),
                    usd_value=FVal(456) * aave_prices[stable_debt_eth_usdc],
                ),
                variable_debt_eth_usdc: Balance(
                    amount=FVal(789),
                    usd_value=FVal(789) * aave_prices[variable_debt_eth_usdc],
                ),
            }),
        ),
    }


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x1107F797c1af4982b038Eb91260b3f9A90eecee9', '0x887380Bb5F5fF5C87BEcc46F0867Fec460F7c5a6',
    '0x577e1290fE9561A9654b7b42B1C10c7Ea90c8a07', '0x1b622CA9C74185A7e21351Ae9AC5ea74b9e8a75b',
]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_compound_v3_token_balances_liabilities(
        blockchain: 'ChainsAggregator', ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the balances of compound v3 supplied/borrowed tokens are correct."""
    c_usdc_v3 = EvmToken('eip155:1/erc20:0xc3d688B66703497DAA19211EEdff47f25384cdc3')
    blockchain.ethereum.transactions_decoder.decode_transaction_hashes(
        ignore_cache=True,
        tx_hashes=[
            deserialize_evm_tx_hash('0x0c9276ed2a202b039d5fa6e9749fd19f631c62e8e4beccc2f4dc0358a4882bb1'),  # Borrow 3,500 USDC from cUSDCv3  # noqa: E501
            deserialize_evm_tx_hash('0x13965c2a1ba75dafa060d0bdadd332c9330b9c5819a8fee7d557a937728fa22f'),  # Borrow 42.5043 USDC from USDCv3  # noqa: E501
            deserialize_evm_tx_hash('0xd53dbca004a5f4a178d881e0194c4464ac5fd52db017329be01413514cb4796e'),  # Borrow 594,629.451218 USDC from USDCv3  # noqa: E501
        ],
    )
    compound_v3_balances = Compoundv3Balances(
        database=blockchain.database,
        evm_inquirer=blockchain.ethereum.node_inquirer,
    )
    unique_borrows, underlying_tokens = compound_v3_balances._extract_unique_borrowed_tokens()

    def mock_extract_unique_borrowed_tokens(
            self: 'Compoundv3Balances',  # pylint: disable=unused-argument
    ) -> tuple[dict[EvmToken, list['ChecksumEvmAddress']], dict['ChecksumEvmAddress', EvmToken]]:
        return {
            token: sorted(addresses)  # cast set to list to avoid randomness in VCR
            for token, addresses in unique_borrows.items()
        }, underlying_tokens

    def mock_query_tokens(addresses):
        return ({
            ethereum_accounts[1]: {c_usdc_v3: FVal('0.32795')},
        }, {c_usdc_v3: Price(CURRENT_PRICE_MOCK)}) if len(addresses) != 0 else ({}, {})

    with patch(
        target='rotkehlchen.chain.evm.decoding.compound.v3.balances.Compoundv3Balances._extract_unique_borrowed_tokens',
        new=mock_extract_unique_borrowed_tokens,
    ), patch(
        target='rotkehlchen.chain.evm.tokens.EvmTokens.query_tokens_for_addresses',
        side_effect=mock_query_tokens,
    ):
        blockchain.query_eth_balances()

    def get_balance(amount: str):
        return Balance(
            amount=FVal(amount), usd_value=FVal(amount) * CURRENT_PRICE_MOCK,
        )
    assert blockchain.balances.eth[ethereum_accounts[0]].liabilities[A_USDC] == get_balance('166903.779933')  # noqa: E501
    assert blockchain.balances.eth[ethereum_accounts[1]].assets[c_usdc_v3] == get_balance('0.32795')  # noqa: E501
    assert blockchain.balances.eth[ethereum_accounts[2]].liabilities[A_USDC] == get_balance('257.565053')  # noqa: E501
    assert blockchain.balances.eth[ethereum_accounts[3]].liabilities[A_USDC] == get_balance('589398.492789')  # noqa: E501
