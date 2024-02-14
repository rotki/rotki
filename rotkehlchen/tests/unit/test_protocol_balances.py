from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.convex.balances import ConvexBalances
from rotkehlchen.chain.ethereum.modules.curve.balances import CurveBalances
from rotkehlchen.chain.ethereum.modules.eigenlayer.balances import EigenlayerBalances
from rotkehlchen.chain.ethereum.modules.octant.balances import OctantBalances
from rotkehlchen.chain.ethereum.modules.thegraph.balances import ThegraphBalances
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.balances import VelodromeBalances
from rotkehlchen.constants.assets import A_CVX, A_GLM, A_GRT, A_STETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, deserialize_evm_tx_hash

if TYPE_CHECKING:
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
    assert user_balance[asset] == Balance(
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
    assert user_balance[asset] == Balance(
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
    assert user_balance[A_CVX.resolve_to_evm_token()] == Balance(
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
    assert user_balance[A_CVX.resolve_to_evm_token()] == Balance(
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
    assert user_balance[Asset(weth_op_lp_token).resolve_to_evm_token()] == Balance(
        amount=FVal('0.043087772070655563'),  # staked in gauge
        usd_value=FVal('0.0646316581059833445'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB9a398aAA3B8890aBbd49e2161Aff629A550152e']])
def test_thegraph_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of GRT currently delegated to indexers are properly detected."""
    tx_hex = deserialize_evm_tx_hash('0x009cd8eccb0637a381d00082056654c534c9e74aa7c1b60196c50b6638236c08')  # noqa: E501
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
    assert user_balance[A_GRT.resolve_to_evm_token()] == Balance(
        amount=FVal('1293.499999999999900000'),
        usd_value=FVal('1940.24999999999985'),
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
    assert user_balance[A_GLM.resolve_to_evm_token()] == Balance(amount=FVal('1000'), usd_value=FVal('1500'))  # noqa: E501


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
    assert balances[ethereum_accounts[0]][A_STETH.resolve_to_evm_token()] == Balance(
        amount=FVal('0.114063122816914142'),
        usd_value=FVal('0.1710946842253712130'),
    )
