import datetime
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.aggregator import CHAIN_TO_BALANCE_PROTOCOLS
from rotkehlchen.chain.arbitrum_one.modules.gearbox.balances import (
    GearboxBalances as GearboxBalancesArbitrumOne,
)
from rotkehlchen.chain.arbitrum_one.modules.gearbox.constants import GEAR_TOKEN_ARB
from rotkehlchen.chain.arbitrum_one.modules.gmx.balances import GmxBalances
from rotkehlchen.chain.arbitrum_one.modules.gmx.constants import CPT_GMX
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.balances import HyperliquidBalances
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.constants import CPT_HYPER
from rotkehlchen.chain.arbitrum_one.modules.thegraph.balances import (
    ThegraphBalances as ThegraphBalancesArbitrumOne,
)
from rotkehlchen.chain.arbitrum_one.modules.umami.balances import UmamiBalances
from rotkehlchen.chain.arbitrum_one.modules.umami.constants import CPT_UMAMI
from rotkehlchen.chain.base.modules.aerodrome.balances import AerodromeBalances
from rotkehlchen.chain.base.modules.extrafi.balances import ExtrafiBalances as ExtrafiBalancesBase
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.aave.balances import AaveBalances
from rotkehlchen.chain.ethereum.modules.blur.balances import BlurBalances
from rotkehlchen.chain.ethereum.modules.blur.constants import BLUR_IDENTIFIER, CPT_BLUR
from rotkehlchen.chain.ethereum.modules.convex.balances import CPT_CONVEX, ConvexBalances
from rotkehlchen.chain.ethereum.modules.curve.balances import CurveBalances
from rotkehlchen.chain.ethereum.modules.curve.crvusd.balances import CurveCrvusdBalances
from rotkehlchen.chain.ethereum.modules.eigenlayer.balances import EigenlayerBalances
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import CPT_EIGENLAYER
from rotkehlchen.chain.ethereum.modules.gearbox.balances import GearboxBalances
from rotkehlchen.chain.ethereum.modules.gearbox.constants import GEAR_TOKEN
from rotkehlchen.chain.ethereum.modules.hedgey.balances import HedgeyBalances
from rotkehlchen.chain.ethereum.modules.hedgey.constants import CPT_HEDGEY
from rotkehlchen.chain.ethereum.modules.octant.balances import OctantBalances
from rotkehlchen.chain.ethereum.modules.octant.constants import CPT_OCTANT
from rotkehlchen.chain.ethereum.modules.pendle.balances import PendleBalances
from rotkehlchen.chain.ethereum.modules.pendle.constants import PENDLE_TOKEN
from rotkehlchen.chain.ethereum.modules.safe.balances import SafeBalances
from rotkehlchen.chain.ethereum.modules.safe.constants import CPT_SAFE, SAFE_TOKEN_ID
from rotkehlchen.chain.ethereum.modules.thegraph.balances import ThegraphBalances
from rotkehlchen.chain.ethereum.utils import should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE, CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.compound.v3.balances import Compoundv3Balances
from rotkehlchen.chain.evm.decoding.compound.v3.constants import CPT_COMPOUND_V3
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.curve.lend.balances import CurveLendBalances
from rotkehlchen.chain.evm.decoding.extrafi.cache import (
    get_existing_reward_pools,
    query_extrafi_data,
)
from rotkehlchen.chain.evm.decoding.extrafi.constants import CPT_EXTRAFI
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.chain.evm.decoding.giveth.constants import CPT_GIVETH
from rotkehlchen.chain.evm.decoding.hop.balances import HopBalances
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.uniswap.v3.balances import UniswapV3Balances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME
from rotkehlchen.chain.evm.tokens import TokenBalancesType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.giveth.balances import GivethBalances as GivethGnosisBalances
from rotkehlchen.chain.optimism.modules.extrafi.balances import ExtrafiBalances
from rotkehlchen.chain.optimism.modules.giveth.balances import (
    GivethBalances as GivethOptimismBalances,
)
from rotkehlchen.chain.optimism.modules.velodrome.balances import VelodromeBalances
from rotkehlchen.chain.optimism.modules.walletconnect.balances import WalletconnectBalances
from rotkehlchen.chain.optimism.modules.walletconnect.constants import (
    CPT_WALLETCONNECT,
    WCT_TOKEN_ID,
)
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_ARB,
    A_CVX,
    A_ENS,
    A_ETH,
    A_GLM,
    A_GMX,
    A_GRT,
    A_GRT_ARB,
    A_STETH,
    A_USDC,
    A_WBTC,
    A_WETH_ARB,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_get_unique_cache_last_queried_ts_by_key,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.unit.decoders.test_curve_crvusd import (
    fixture_crvusd_controller,  # noqa: F401
)
from rotkehlchen.tests.unit.decoders.test_curve_lend import (
    fixture_arbitrum_vault_token,  # noqa: F401
    fixture_arbitrum_vault_underlying_token,  # noqa: F401
)
from rotkehlchen.tests.utils.arbitrum_one import get_arbitrum_allthatnode
from rotkehlchen.tests.utils.balances import find_inheriting_classes
from rotkehlchen.tests.utils.constants import CURRENT_PRICE_MOCK
from rotkehlchen.tests.utils.ethereum import (
    INFURA_ETH_NODE,
    get_decoded_events_of_transaction,
    wait_until_all_nodes_connected,
)
from rotkehlchen.types import (
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Price,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CURVE]])
@pytest.mark.parametrize('ethereum_accounts', [['0xb24cE065a3A9bbCCED4B74b6F4435b852286396d']])
def test_curve_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x09b67a0846ce2f6bea50221cfb5ac67f5b2f55b89300e45f58bf2f69dc589d43')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    curve_balances_inquirer = CurveBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    curve_balances = curve_balances_inquirer.query_balances()
    user_balance = curve_balances[ethereum_accounts[0]]
    asset = EvmToken('eip155:1/erc20:0xC25a3A3b969415c80451098fa907EC722572917F')
    assert user_balance.assets[asset][CPT_CURVE] == Balance(
        amount=FVal('2402.233522210805651105'),
        usd_value=FVal('3603.3502833162084766575'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CONVEX]])
@pytest.mark.parametrize('ethereum_accounts', [['0x53913A03a065f685097f8E8f40284D58016bB0F9']])
def test_convex_gauges_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf9d35b99cd67a506d216dbfeaaeb89adcfb3b8d104f2d863c97278eacee1bc41')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    convex_balances_inquirer = ConvexBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    convex_balances = convex_balances_inquirer.query_balances()
    user_balance = convex_balances[ethereum_accounts[0]]
    asset = EvmToken('eip155:1/erc20:0xF9835375f6b268743Ea0a54d742Aa156947f8C06')
    assert user_balance.assets[asset][CPT_CONVEX] == Balance(
        amount=FVal('34.011048723934089999'),
        usd_value=FVal('51.0165730859011349985'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_CONVEX]])
@pytest.mark.parametrize('ethereum_accounts', [['0x36928dCA92EA4eDA2292d0090e60532eB6A32475']])
def test_convex_staking_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check Convex balance query for CVX locked and staked"""
    tx_hash = deserialize_evm_tx_hash('0x9a1cdbbe383d7677cf45b54106af0cf7e07f65eb1809f9bd3ecea8bb905600d3')  # noqa: E501
    _, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    tx_hash_2 = deserialize_evm_tx_hash('0x49f4dabfee05cc78e2b19a574373ad5afb1de52e03d7b355fe8611be7137e411')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash_2,
    )
    convex_balances_inquirer = ConvexBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    convex_balances = convex_balances_inquirer.query_balances()
    user_balance = convex_balances[ethereum_accounts[0]]
    # the amount here is the sum of the locked ~44 and the staked tokens ~333
    assert user_balance.assets[A_CVX.resolve_to_evm_token()][CPT_CONVEX] == Balance(
        amount=FVal('18229.934390350508148387'),
        usd_value=FVal('27344.9015855257622225805'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x36928dCA92EA4eDA2292d0090e60532eB6A32475']])
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
    tx_hash = deserialize_evm_tx_hash('0x49f4dabfee05cc78e2b19a574373ad5afb1de52e03d7b355fe8611be7137e411')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    convex_balances_inquirer = ConvexBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    convex_balances = convex_balances_inquirer.query_balances()
    user_balance = convex_balances[ethereum_accounts[0]]
    assert user_balance.assets[A_CVX.resolve_to_evm_token()][CPT_CONVEX] == Balance(
        amount=FVal('18229.934390350508148387'),
        usd_value=FVal('27344.9015855257622225805'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_velodrome_v2_staking_balances(
        optimism_inquirer: 'OptimismInquirer',
        optimism_transaction_decoder: 'OptimismTransactionDecoder',
        optimism_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of velodrome v2 gauges are properly queried."""
    tx_hash = deserialize_evm_tx_hash('0xed7e13e4941bba33edbbd70c4f48c734629fd67fe4eac43ce1bed3ef8f3da7df')  # transaction that interacts with the gauge address  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(  # decode events that interact with the gauge address  # noqa: E501
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    balances_inquirer = VelodromeBalances(
        evm_inquirer=optimism_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances()  # queries the gauge balance of the address if the address has interacted with a known gauge  # noqa: E501
    user_balance = balances[optimism_accounts[0]]
    weth_op_lp_token = evm_address_to_identifier(
        address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        token_type=TokenKind.ERC20,
    )
    assert user_balance.assets[Asset(weth_op_lp_token).resolve_to_evm_token()][CPT_VELODROME] == Balance(  # noqa: E501
        amount=FVal('0.043087772070655563'),  # staked in gauge
        usd_value=FVal('0.0646316581059833445'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x72296d54B83491c59236E45F19b6fdE8a2B2771b']])
def test_thegraph_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of GRT currently delegated to indexers are properly detected."""
    tx_hash = deserialize_evm_tx_hash('0x81cdf7a4201d3e89c9f3a8d3ae18e3cb7ae0e06a5cbc514f1e41504b9b263667')  # noqa: E501
    amount = '6626.873960369737'
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    thegraph_balances_inquirer = ThegraphBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    thegraph_balances = thegraph_balances_inquirer.query_balances()
    user_balance = thegraph_balances[ethereum_accounts[0]]
    assert user_balance.assets[A_GRT][CPT_THEGRAPH] == Balance(
        amount=FVal(amount),
        usd_value=FVal(amount) * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xA9728D95567410555557a54EcA320e5E8bEa36a5']])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(get_arbitrum_allthatnode(weight=ONE, owned=True),)])  # noqa: E501
def test_thegraph_balances_arbitrum_one(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
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
    tx_hash = deserialize_evm_tx_hash('0x3c846f305330969fb0ddb87c5ae411b4e9692f451a7ff3237b6f71020030c7d1')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    thegraph_balances_inquirer = ThegraphBalancesArbitrumOne(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    thegraph_balances = thegraph_balances_inquirer.query_balances()
    user_balance = thegraph_balances[arbitrum_one_accounts[0]]
    assert user_balance.assets[A_GRT_ARB][CPT_THEGRAPH] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_thegraph_balances_vested_arbitrum_one(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_transaction_decoder: 'ArbitrumOneTransactionDecoder',
        ethereum_inquirer: 'EthereumInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances of GRT currently vested are properly detected."""
    expected_grt_balance = FVal('246914.881548572905')
    # decode the delegation transfer event which has the vested contract address as delegator_l2
    for tx_hash in (
        '0x48321bb00e5c5b67f080991864606dbc493051d20712735a579d7ae31eca3d78',
        '0xed80711e4cb9c428790f0d9b51f79473bf5253d5d03c04d958d411e7fa34a92e',
    ):
        get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
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
            return sorted(result)

        return wrapper(events)

    # Patch it to guarantee order of returned list and thus
    # making the test's remote calls deterministic for VCR
    with patch(
        'rotkehlchen.chain.arbitrum_one.modules.thegraph.balances.ThegraphBalances.process_staking_events',
        new=mock_process_staking_events,
    ):
        thegraph_balances_inquirer = ThegraphBalancesArbitrumOne(
            evm_inquirer=arbitrum_one_inquirer,
            tx_decoder=arbitrum_one_transaction_decoder,
        )
        thegraph_balances = thegraph_balances_inquirer.query_balances()
    assert thegraph_balances[arbitrum_one_accounts[0]].assets[A_GRT_ARB][CPT_THEGRAPH] == Balance(
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
    tx_hash = deserialize_evm_tx_hash('0x29944efad254413b5eccdd5f13f14642ab830dbf51d5f2cfc59cf4957f33671a')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    octant_balances_inquirer = OctantBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    octant_balances = octant_balances_inquirer.query_balances()
    user_balance = octant_balances[ethereum_accounts[0]]
    assert user_balance.assets[A_GLM.resolve_to_evm_token()][CPT_OCTANT] == Balance(amount=FVal('1000'), usd_value=FVal('1500'))  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x15AcAA0E27b70AfE3D7631cDAf5516BCAbE3bc0F']])
def test_eigenlayer_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x89981857ab9f31369f954ae332ffd910e1f3c8efe531efde5f26666316855591')  # noqa: E501
    events, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert len(events) == 2
    balances_inquirer = EigenlayerBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances()
    assert balances[ethereum_accounts[0]].assets[A_STETH.resolve_to_evm_token()][CPT_EIGENLAYER] == Balance(  # noqa: E501
        amount=FVal('0.114063122816914142'),
        usd_value=FVal('0.1710946842253712130'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x789E8DD02FfCCd7A753B048559d4FBeA1e1a1b7c']])
def test_eigenpod_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_transaction_decoder: 'EthereumTransactionDecoder',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb6fa282227916f9b16df953f79a5859ba80b8bc3b9c6adc01f262070d3c9e3d5')  # noqa: E501
    events, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert len(events) == 2
    balances_inquirer = EigenlayerBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    eigenpod_balance = FVal('0.054506232')
    balances = balances_inquirer.query_balances()
    assert balances[ethereum_accounts[0]].assets[A_ETH][CPT_EIGENLAYER] == Balance(
        amount=eigenpod_balance,
        usd_value=FVal('1.5') * eigenpod_balance,
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
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """
    Test querying balances for GMX. We use an address with 2 different positions and the other
    one has a single position. There are both shorts and longs in the data.
    """
    for tx_hex in (
        '0x195cdb1bde8da223c7e6216166f7e8b5b79fee6409dde145a8f3e95223ebcc51',  # short btc
        '0x59d136f8d1b366a895ddf4136fb45d62b862e79f4a937f5a9b33ceec47eaf32f',  # long btc
        '0xf14d5a3f3fa4a4c324f95b70db81502f3d7c1910782381ed82f3580da64b093f',  # long eth
    ):
        tx_hash = deserialize_evm_tx_hash(tx_hex)
        _, tx_decoder = get_decoded_events_of_transaction(
            evm_inquirer=arbitrum_one_inquirer,
            tx_hash=tx_hash,
        )

    balances_inquirer = GmxBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
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

    weth_arb = Asset('eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
    assert balances[arbitrum_one_accounts[0]].assets[weth_arb][CPT_GMX] == Balance(
        amount=FVal('0.020625523771241888'),
        usd_value=FVal('73.904758011400794198629853957124'),
    )
    wbtc_arb = Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f')
    assert balances[arbitrum_one_accounts[0]].assets[wbtc_arb][CPT_GMX] == Balance(
        amount=FVal('0.00092231'),
        usd_value=FVal('64.495126014300507906764604009528'),
    )
    dai_arb = Asset('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')
    assert balances[arbitrum_one_accounts[1]].assets[dai_arb][CPT_GMX] == Balance(
        amount=FVal('42.896760410410693074'),
        usd_value=FVal('42.939657170821103766867050208907'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3D3db31AdbCCB6a4e5aE94ec0701d361E147FA6A']])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(get_arbitrum_allthatnode(weight=ONE, owned=True),)])  # noqa: E501
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_gmx_balances_staking(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
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
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x25160bf17e5a77935c7661933c045739dba44606859a20f00f187ef291e56a8f'),
    )
    balances_inquirer = GmxBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances()
    assert balances[arbitrum_one_accounts[0]].assets[A_GMX][CPT_GMX] == Balance(
        amount=FVal('4.201981641893733976'),
        usd_value=FVal('164.46556146372074782064'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6A61Ea7832f84C3096c70f042aB88D9a56732D7B']])
def test_aave_balances_staking(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Test the balance query for staked AAVE balances. It adds a staking event
    and then queries the balances for that address."""
    amount = FVal('0.134274348203440352')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xfaf96358784483a96a61db6aa4ecf4ac87294b841671ca208de6b5d8f83edf17'),
    )
    balances_inquirer = AaveBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances()
    assert balances[ethereum_accounts[0]].assets[A_AAVE][CPT_AAVE] == Balance(
        amount=amount, usd_value=amount * FVal(1.5),
    )


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
        token_kind=TokenKind.ERC20,
        symbol='aEthUSDC',
        protocol=CPT_AAVE_V3,
    )
    stable_debt_eth_usdc = get_or_create_evm_token(
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0xB0fe3D292f4bd50De902Ba5bDF120Ad66E9d7a39'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        symbol='stableDebtEthUSDC',
        protocol=CPT_AAVE_V3,
    )
    variable_debt_eth_usdc = get_or_create_evm_token(
        userdb=blockchain.database,
        evm_address=string_to_evm_address('0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
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

    balances: defaultdict[ChecksumEvmAddress, BalanceSheet] = defaultdict(BalanceSheet)
    with patch.object(
        target=ethereum_manager.tokens,
        attribute='query_tokens_for_addresses',
        new=mock_new_balances,
    ):
        blockchain.query_evm_tokens(manager=ethereum_manager, balances=balances)

    # Check individual balances instead of full BalanceSheet comparison
    assert balances[blockchain.accounts.eth[0]].assets[a_eth_usdc][CPT_AAVE_V3] == Balance(
        amount=FVal(123),
        usd_value=FVal(123) * aave_prices[a_eth_usdc],
    )
    assert balances[blockchain.accounts.eth[0]].liabilities[stable_debt_eth_usdc][CPT_AAVE_V3] == Balance(  # noqa: E501
        amount=FVal(456),
        usd_value=FVal(456) * aave_prices[stable_debt_eth_usdc],
    )
    assert balances[blockchain.accounts.eth[1]].liabilities[stable_debt_eth_usdc][CPT_AAVE_V3] == Balance(  # noqa: E501
        amount=FVal(456),
        usd_value=FVal(456) * aave_prices[stable_debt_eth_usdc],
    )
    assert balances[blockchain.accounts.eth[1]].liabilities[variable_debt_eth_usdc][CPT_AAVE_V3] == Balance(  # noqa: E501
        amount=FVal(789),
        usd_value=FVal(789) * aave_prices[variable_debt_eth_usdc],
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x1107F797c1af4982b038Eb91260b3f9A90eecee9', '0x887380Bb5F5fF5C87BEcc46F0867Fec460F7c5a6',
]])
def test_compound_v3_token_balances_liabilities(
        blockchain: 'ChainsAggregator', ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the balances of compound v3 supplied/borrowed tokens are correct."""
    c_usdc_v3 = EvmToken('eip155:1/erc20:0xc3d688B66703497DAA19211EEdff47f25384cdc3')

    with (
        patch(
            target='rotkehlchen.chain.ethereum.node_inquirer.EthereumInquirer.ensure_cache_data_is_updated',
        ),
        patch(
            target='rotkehlchen.chain.ethereum.modules.yearn.decoder.should_update_protocol_cache',
        ),
        patch(
            target='rotkehlchen.chain.evm.decoding.morpho.decoder.should_update_protocol_cache',
        ),
        patch(
            target='rotkehlchen.chain.evm.decoding.stakedao.decoder.should_update_protocol_cache',
        ),
        patch(
            target='rotkehlchen.chain.evm.decoding.curve.lend.decoder.should_update_protocol_cache',
        ),
        patch(
            target='rotkehlchen.chain.ethereum.modules.curve.crvusd.decoder.should_update_protocol_cache',
        ),
        patch(
            target='rotkehlchen.chain.evm.decoding.pendle.decoder.should_update_protocol_cache',
            return_value=False,
        ),
        patch(
            target='rotkehlchen.chain.evm.decoding.beefy_finance.decoder.should_update_protocol_cache',
            return_value=False,
        ),
    ):
        blockchain.ethereum.transactions_decoder.decode_transaction_hashes(
            ignore_cache=True,
            tx_hashes=[
                deserialize_evm_tx_hash('0x0c9276ed2a202b039d5fa6e9749fd19f631c62e8e4beccc2f4dc0358a4882bb1'),  # Borrow 3,500 USDC from cUSDCv3  # noqa: E501
                deserialize_evm_tx_hash('0x13965c2a1ba75dafa060d0bdadd332c9330b9c5819a8fee7d557a937728fa22f'),  # Borrow 42.5043 USDC from USDCv3  # noqa: E501
                deserialize_evm_tx_hash('0xd53dbca004a5f4a178d881e0194c4464ac5fd52db017329be01413514cb4796e'),  # Borrow 594,629.451218 USDC from USDCv3  # noqa: E501
            ],
        )
    compound_v3_balances = Compoundv3Balances(
        evm_inquirer=blockchain.ethereum.node_inquirer,
        tx_decoder=blockchain.ethereum.transactions_decoder,
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
    assert blockchain.balances.eth[ethereum_accounts[0]].liabilities[A_USDC][CPT_COMPOUND_V3] == get_balance('48076.773054')  # noqa: E501
    assert blockchain.balances.eth[ethereum_accounts[1]].assets[c_usdc_v3][CPT_COMPOUND_V3] == get_balance('0.32795')  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_blur_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances of Blur are properly detected."""
    tx_hash = deserialize_evm_tx_hash('0x09b9d311c62dadc69a06f39daa5206760f38ef48d9e8473f27a9cf2d599133c9')  # noqa: E501
    amount = FVal('6350.3577325406')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    blur_balances_inquirer = BlurBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    blur_balances = blur_balances_inquirer.query_balances()
    user_balance = blur_balances[ethereum_accounts[0]]
    assert user_balance.assets[Asset(BLUR_IDENTIFIER)][CPT_BLUR] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_hop_balances_staking(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Test the balance query for staked hop lp balances. It adds a staking event
    and then queries the balances for that address."""
    lp_amount, reward_amount = FVal('0.005676129314105837'), FVal('0.06248913329652552')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x6329984b82cb85903fee9fef61fb77cdf848ff6344056156da2e66676ad91473'),
    )
    balances_inquirer = HopBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances()
    hop_lp_token = Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a')
    hop_reward_token = Asset('eip155:42161/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC')
    assert balances[arbitrum_one_accounts[0]].assets[hop_lp_token][CPT_HOP] == Balance(
        amount=lp_amount, usd_value=lp_amount * FVal(1.5),
    )
    assert balances[arbitrum_one_accounts[0]].assets[hop_reward_token][CPT_HOP] == Balance(
        amount=reward_amount, usd_value=reward_amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_hop_balances_staking_2(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Test the balance query for staked hop lp balances. It adds a staking event
    and then queries the balances for that address."""
    lp_amount, reward_amount = FVal('0.005676129314105837'), FVal('0.008945843949587174')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xe0c1f6f152422784a4e4346d84af7d32fda95eab17da257f3fdc5121f4a6fbc8'),
    )
    balances_inquirer = HopBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    balances = balances_inquirer.query_balances()
    hop_lp_token = Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a')
    assert balances[arbitrum_one_accounts[0]].assets[hop_lp_token][CPT_HOP] == Balance(
        amount=lp_amount, usd_value=lp_amount * FVal(1.5),
    )
    assert balances[arbitrum_one_accounts[0]].assets[A_ARB][CPT_HOP] == Balance(
        amount=reward_amount, usd_value=reward_amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_gearbox_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances of Gearbox are properly detected."""
    tx_hash = deserialize_evm_tx_hash('0x5de7647a4c8f8ca1e5434725dd09b27ce05e41954d72c3f1f4d639c8b7019f4a')  # noqa: E501
    amount = FVal('260.869836197270890866')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    protocol_balances_inquirer = GearboxBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[ethereum_accounts[0]]
    assert user_balance.assets[GEAR_TOKEN][CPT_GEARBOX] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc8474089b8A428a32d938f5C28FB7eC8534D6FD1']])
def test_gearbox_balances_arb(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances of Gearbox are properly detected."""
    tx_hash = deserialize_evm_tx_hash('0xd6abdbf2e57c37e191c5e93b9b99d1c70acdca000b2fd9e8236093a0b359221e')  # noqa: E501
    amount = FVal('139896.73226582730792446')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    protocol_balances_inquirer = GearboxBalancesArbitrumOne(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[arbitrum_one_accounts[0]]
    assert user_balance.assets[GEAR_TOKEN_ARB][CPT_GEARBOX] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA76C44d0adD77F9403715D8B6F47AD4e6515EC8c']])
def test_safe_locked(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that locked SAFE balances are properly detected."""
    tx_hash = deserialize_evm_tx_hash('0xad3d976ae02cf82f109cc2d2f3e8f2f10df6a00a4825e3f04cf0e1b7e68a06b8')  # noqa: E501
    amount = FVal('11515.763372')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    protocol_balances_inquirer = SafeBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[ethereum_accounts[0]]
    assert user_balance.assets[Asset(SAFE_TOKEN_ID)][CPT_SAFE] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('optimism_accounts', [[
    '0x4ba257EC214BA1e6a3b4E46Bd7C4654b9E81CED3',
    '0xf34743D4F4C2f9276ED6dda070CB695ebB24aA62',
]])
def test_extrafi_lending_balances(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list[ChecksumEvmAddress],
        globaldb: 'GlobalDBHandler',
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances for extrafi both for lending and locking extra are queried correctly"""
    for tx_hex in (
        '0x1886c8169b096df75061e2fec93df029c42325f2f7066535ecc07a504efc5e92',  # lock extra
        '0x81a87d2f8a9752ac4889ec92d6ec553417e3b4cc709a240718cf423f362e89b1',  # deposit velo for lending  # noqa: E501
    ):
        tx_hash = deserialize_evm_tx_hash(tx_hex)
        _, tx_decoder = get_decoded_events_of_transaction(
            evm_inquirer=optimism_inquirer,
            tx_hash=tx_hash,
        )
    protocol_balances_inquirer = ExtrafiBalances(
        evm_inquirer=optimism_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances, velo_amount, extra_amount = protocol_balances_inquirer.query_balances(), FVal('366399.179130825123704582'), FVal('6405.478041239509217895')  # noqa: E501
    assert protocol_balances[optimism_accounts[0]].assets[Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db')][CPT_EXTRAFI] == Balance(  # noqa: E501
        amount=velo_amount,
        usd_value=velo_amount * FVal(1.5),
    )
    assert protocol_balances[optimism_accounts[1]].assets[Asset('eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8')][CPT_EXTRAFI] == Balance(  # noqa: E501
        amount=extra_amount,
        usd_value=extra_amount * FVal(1.5),
    )

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            "SELECT key, value FROM unique_cache WHERE key LIKE 'EXTRAFI_LENDING_RESERVES%'",
        ).fetchall() == [(
            'EXTRAFI_LENDING_RESERVES1035',
            '0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db',
        )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('base_accounts', [['0x007183900fBbe3e7815b278074a49B8C7319EDba']])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_extrafi_farm_balances(
        base_inquirer: 'BaseInquirer',
        base_accounts: list[ChecksumEvmAddress],
        globaldb: 'GlobalDBHandler',
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that balances for extrafi farms are queried correctly"""
    tx_hash = deserialize_evm_tx_hash('0xf0458b2c208fa7362669b6430277808a2bda527fcbe5dd3514a5879c445311cc')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
    )
    protocol_balances_inquirer = ExtrafiBalancesBase(
        evm_inquirer=base_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    assert protocol_balances[base_accounts[0]].assets[Asset('eip155:8453/erc20:0x61366A4e6b1DB1b85DD701f2f4BFa275EF271197')][CPT_EXTRAFI] == Balance(  # noqa: E501
        amount=FVal('0.001146519712970269'),
        usd_value=FVal('15072.492806231623823179919568956'),
    )
    assert protocol_balances[base_accounts[0]].liabilities[Asset('eip155:8453/erc20:0xB79DD08EA68A908A97220C76d19A6aA9cBDE4376')][CPT_EXTRAFI] == Balance(  # noqa: E501
        amount=FVal('10015.072706'),
        usd_value=FVal('10012.6978598973939729841870'),
    )

    with globaldb.conn.read_ctx() as cursor:
        assert cursor.execute(
            "SELECT key, value FROM unique_cache WHERE key LIKE 'EXTRAFI_FARM_METADADATA%'",
        ).fetchall() == [(
            'EXTRAFI_FARM_METADADATA845320',
            '["0x61366A4e6b1DB1b85DD701f2f4BFa275EF271197", "0xA3d1a8DEB97B111454B294E2324EfAD13a9d8396", "0xB79DD08EA68A908A97220C76d19A6aA9cBDE4376"]',  # noqa: E501
        )]

    # query again to verify that it works as expected
    assert (protocol_balances := protocol_balances_inquirer.query_balances())[base_accounts[0]].assets[Asset('eip155:8453/erc20:0x61366A4e6b1DB1b85DD701f2f4BFa275EF271197')][CPT_EXTRAFI] == Balance(  # noqa: E501
        amount=FVal('0.001146519712970269'),
        usd_value=FVal('15072.492806231623823179919568956'),
    )
    assert protocol_balances[base_accounts[0]].liabilities[Asset('eip155:8453/erc20:0xB79DD08EA68A908A97220C76d19A6aA9cBDE4376')][CPT_EXTRAFI] == Balance(  # noqa: E501
        amount=FVal('10015.072706'),
        usd_value=FVal('10012.6978598973939729841870'),
    )


@pytest.mark.freeze_time
@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_extrafi_cache(optimism_inquirer: 'OptimismInquirer', freezer):
    """Check that the cache gets populated and timestamp updated if
    we requery again"""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            "DELETE FROM general_cache WHERE key LIKE 'EXTRAFI%'",
        )
        write_cursor.execute(
            "DELETE FROM unique_cache WHERE key LIKE 'EXTRAFI%'",
        )

    start_ts = 1727436933
    freezer.move_to(datetime.datetime.fromtimestamp(start_ts, tz=datetime.UTC))
    query_extrafi_data(
        inquirer=optimism_inquirer,
        cache_type=CacheType.EXTRAFI_NEXT_RESERVE_ID,
        msg_aggregator=optimism_inquirer.database.msg_aggregator,
        reload_all=False,
    )
    chain = str(optimism_inquirer.chain_id.serialize_for_db())
    with GlobalDBHandler().conn.read_ctx() as cursor:
        existing_pools = get_existing_reward_pools(chain_id=ChainID.OPTIMISM)
        assert '0x1A6cB72ba9aD6Cf0855D5B497e8E1485A3B3FE39' in existing_pools[0]
        last_queried_ts = globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.EXTRAFI_NEXT_RESERVE_ID, chain),
        )
        assert should_update_protocol_cache(
            userdb=optimism_inquirer.database,
            cache_key=CacheType.EXTRAFI_NEXT_RESERVE_ID,
            args=(chain,),
        ) is False

    freezer.move_to(datetime.datetime.fromtimestamp(start_ts + 300, tz=datetime.UTC))
    query_extrafi_data(  # check that the timestamp gets updated
        inquirer=optimism_inquirer,
        cache_type=CacheType.EXTRAFI_NEXT_RESERVE_ID,
        msg_aggregator=optimism_inquirer.database.msg_aggregator,
        reload_all=False,
    )
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_last_queried_ts_by_key(
            cursor=cursor,
            key_parts=(CacheType.EXTRAFI_NEXT_RESERVE_ID, chain),
        ) > last_queried_ts


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_umami_balances(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances of Umami are properly detected."""
    amount, usd_value, gm_usdc_vault = FVal('46.422107'), FVal('74.988646874055'), Asset('eip155:42161/erc20:0x5f851F67D24419982EcD7b7765deFD64fBb50a97')  # noqa: E501
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x4688c10bc6fadf06c2348fffe1e13c6d7a0b0c586438944aa9557b447a5f319a'),
    )

    protocol_balances_inquirer = UmamiBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[arbitrum_one_accounts[0]]
    assert user_balance.assets[gm_usdc_vault][CPT_UMAMI] == Balance(
        amount=amount,
        usd_value=usd_value,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xc0d5dBe750bb5c001Ba8C499385143f566611679']])
def test_walletconnect_staked_balances(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances of walletconnect are properly detected."""
    tx_hash = deserialize_evm_tx_hash('0xcc691ea8eeb56fd5f5ceb98879e3571ee167a2ac4c5bad4c9463127262d096af')  # noqa: E501
    amount = FVal('184.286559270201')
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
    )
    protocol_balances_inquirer = WalletconnectBalances(
        evm_inquirer=optimism_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[optimism_accounts[0]]
    assert user_balance.assets[Asset(WCT_TOKEN_ID)][CPT_WALLETCONNECT] == Balance(
        amount=amount,
        usd_value=amount * FVal(1.5),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_curve_lend_balances(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
        arbitrum_vault_token: 'EvmToken',
) -> None:
    """Check that Curve lending collateral and debt balances are properly detected."""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x58e9068edee8897c5c2e2181cc897ba026efd936f74e14329b64355e82240ea5'),
    )
    protocol_balances_inquirer = CurveLendBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[arbitrum_one_accounts[0]]

    assert user_balance.assets[A_WETH_ARB][CPT_CURVE] == Balance(
        amount=FVal('0.013968407653526627'),
        usd_value=FVal('50.14490726724216773476'),
    )
    assert user_balance.liabilities[Asset('eip155:42161/erc20:0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5')][CPT_CURVE] == Balance(  # noqa: E501
        amount=FVal('30.100455885544052449'),
        usd_value=FVal('30.055997512201103883532827'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0x494FBCf6AB69609732B4c97462FAc7f7cb717015']])
@pytest.mark.parametrize('crvusd_controller', ['0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67'], indirect=True)  # noqa: E501
def test_curve_crvusd_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
        crvusd_controller: 'ChecksumEvmAddress',
) -> None:
    """Check that Curve lending collateral and debt balances are properly detected."""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x7acdf5d10091405762dc3f2658e6da0fdd9cb42a74c55b944c2e88b089eb15cc'),
    )
    protocol_balances_inquirer = CurveCrvusdBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[ethereum_accounts[0]]

    assert user_balance.assets[A_WBTC][CPT_CURVE] == Balance(
        amount=FVal('0.04999999'),
        usd_value=FVal('4251.14914977'),
    )
    assert user_balance.liabilities[Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E')][CPT_CURVE] == Balance(  # noqa: E501
        amount=FVal('3591.07534296748961703'),
        usd_value=FVal('3591.04302328940290962344673'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('gnosis_accounts', [['0x839395e20bbB182fa440d08F850E6c7A8f6F0780']])
def test_gnosis_giveth_staked_balances(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances in Giveth Gnosis are properly detected"""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x9cd449bab5d207bb5c72d681efb94f7c1643addfc41003ed7fc5a58cb7f0f265'),
    )
    protocol_balances_inquirer = GivethGnosisBalances(
        evm_inquirer=gnosis_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[gnosis_accounts[0]]
    giv_asset = Asset(protocol_balances_inquirer.giv_token_id)

    assert user_balance.assets[giv_asset][CPT_GIVETH] == Balance(
        amount=FVal('21266652.068337565927179618'),
        usd_value=FVal('170838.63139580728447924149192906'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('optimism_accounts', [['0x9924285ff2207D6e36642B6832A515A6a3aedCAB']])
def test_optimism_giveth_staked_balances(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list[ChecksumEvmAddress],
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that staked balances in Giveth Optimism are properly detected"""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x06a3f05d3441d4eb36c3497ddffbfaef059a47c735f6efa317ae0ba5962ed46c'),
    )
    protocol_balances_inquirer = GivethOptimismBalances(
        evm_inquirer=optimism_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[optimism_accounts[0]]
    giv_asset = Asset(protocol_balances_inquirer.giv_token_id)

    assert user_balance.assets[giv_asset][CPT_GIVETH] == Balance(
        amount=FVal('31641.865744797163817899'),
        usd_value=FVal('247.43907370565637308433200101'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
@pytest.mark.parametrize('ethereum_accounts', [['0x561fe975d925CC259D5aFF7A4d83612Fb4758103']])
def test_uniswapv3_balances_ethereum(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that Uniswap V3 LP positions are properly detected on ethereum"""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xc20a48dc99d805116ac94ce8a7f669ce174d7cefa6712c3858b605365c314f80'),
    )
    protocol_balances_inquirer = UniswapV3Balances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[ethereum_accounts[0]]
    position_nft = Asset('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/931287')
    assert user_balance.assets[position_nft][CPT_UNISWAP_V3] == Balance(
        amount=ONE,
        usd_value=FVal('1079.26539536305871313957103164322012047931617819770314565623847023176368686119'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('base_accounts', [['0xD79B70C1D4Ab78Cd97d53508b5CBf0D573728980']])
def test_uniswapv3_balances_base(
        base_inquirer: 'BaseInquirer',
        base_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that Uniswap V3 LP positions are properly detected on base"""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x0de888bf954f77a48d9e538c60e4e8763b066660b9570840d5299e9c604d60a3'),
    )
    protocol_balances_inquirer = UniswapV3Balances(
        evm_inquirer=base_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[base_accounts[0]]
    position_nft = Asset('eip155:8453/erc721:0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1/1797484')
    assert user_balance.assets[position_nft][CPT_UNISWAP_V3] == Balance(
        amount=ONE,
        usd_value=FVal('2874.37501899742102833253858580810245123589303319863408360101801493666273901534'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_uniswapv3_balances_arbitrum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that Uniswap V3 LP positions are properly detected on arbitrum"""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x59c14ea121a693a2da3503cb3734baa35efc7d75c8e8b1fb1e9b474af7decde0'),
    )
    protocol_balances_inquirer = UniswapV3Balances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[arbitrum_one_accounts[0]]
    position_nft = Asset('eip155:42161/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/4085191')
    assert user_balance.assets[position_nft][CPT_UNISWAP_V3] == Balance(
        amount=ONE,
        usd_value=FVal('26.7962165816347802200022991318482105023701331828161909334783235019695249285796'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0x54BeCc7560a7Be76d72ED76a1f5fee6C5a2A7Ab6']])
def test_hedgey_locked_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check that hedgey locked voting token positions are detected"""
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xb85eb3fb6496fa51ac3d43d230ea729b52593bd2781b2b9dfab638aab7011719'),
    )
    protocol_balances_inquirer = HedgeyBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[ethereum_accounts[0]]

    assert user_balance.assets[A_ENS][CPT_HEDGEY] == Balance(
        amount=FVal('2943.901116977446327568'),
        usd_value=FVal('92114.66595022429558960272'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('optimism_accounts', [['0xD4dd9a1FAc6D7bBe327c2b4A5Dc3197D0B10874b']])
def test_velodrome_locked_balances(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x8747ae5f08613802c76f3c6d4517c87c2133b0231990dd30df32b8c9bb9fa7a1'),
    )
    protocol_balances_inquirer = VelodromeBalances(
        evm_inquirer=optimism_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[optimism_accounts[0]]
    assert user_balance.assets[Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db')][CPT_VELODROME] == Balance(  # noqa: E501
        amount=FVal('215.817657296359655794'),
        usd_value=FVal('12.717487091502585436973038'),
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('base_accounts', [['0xD10c1617e7afF13759Ad45AA373E89d5251B37cC']])
def test_aerodrome_locked_balances(
        base_inquirer: 'BaseInquirer',
        base_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x637a00989340052bbb5a6b63c012c70a3b695223a0da5da95e9b233a524908e2'),
    )
    protocol_balances_inquirer = AerodromeBalances(
        evm_inquirer=base_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[base_accounts[0]]
    assert user_balance.assets[Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631')][CPT_AERODROME] == Balance(  # noqa: E501
        amount=FVal('927'),
        usd_value=FVal('538.76313'),
    )


def test_all_balance_classes_used():
    """
    Test that all protocol balance classes are used properly in the
    CHAIN_TO_BALANCE_PROTOCOLS mapping
    """
    classes = find_inheriting_classes(
        root_directory=(root_directory := Path(__file__).resolve().parent.parent.parent),
        search_directory=root_directory / 'chain',
        base_class=ProtocolWithBalance,
        exclude_class_names={
            'GearboxCommonBalances',
            'ExtrafiCommonBalances',
            'VelodromeLikeBalances',
            'GivethCommonBalances',
        },
    )
    unused_classes = set()

    for class_entry in classes:
        for balances in CHAIN_TO_BALANCE_PROTOCOLS.values():
            if class_entry in balances:
                break
        else:  # not found
            unused_classes.add(class_entry)

    assert unused_classes == set(), f'Found unused classes {unused_classes}'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('arbitrum_one_accounts', [[
    '0x4E60C2E7181EDFc5471C0cBC8D485706d1b35686',
    '0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF',
]])
def test_hyperliquid(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    """Check balances in hyperliquid both for spot and perp
    0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF has mainly spot and
    0x4E60C2E7181EDFc5471C0cBC8D485706d1b35686 has mainly perp balances.
    """
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x2aa0a70af2347ccc4ba3d5f4eddd362c7cd8118c0f2a3617d4b4fcf78c929ea7'),
    )
    get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x2e9ef8a4369c33f1b3adb0d870fc60a1f721cbf4bda1181d6804acb0f41a2d66'),
    )
    hyper_balances = HyperliquidBalances(
        evm_inquirer=arbitrum_one_inquirer,
        tx_decoder=tx_decoder,
    )
    arb_usdc = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
    # ensure mappings are set
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO counterparty_asset_mappings (counterparty, symbol, local_id) VALUES (?, ?, ?)',  # noqa: E501
            [
                (CPT_HYPER, 'HYPE', 'HYPE'),
                (CPT_HYPER, 'USDC', arb_usdc.identifier),
            ],

        )

    protocol_balances = hyper_balances.query_balances()
    user_4e = arbitrum_one_accounts[0]
    user_3b = arbitrum_one_accounts[1]
    assert protocol_balances[user_4e].assets[arb_usdc][CPT_HYPER] == Balance(amount=FVal(519.955570), usd_value=FVal(519.887455820330))  # noqa: E501
    assert protocol_balances[user_3b].assets[Asset('HYPE')][CPT_HYPER] == Balance(amount=FVal(14.79852012), usd_value=FVal(232.9287066888))  # noqa: E501
    assert protocol_balances[user_3b].assets[arb_usdc][CPT_HYPER] == Balance(amount=FVal(27.20794226), usd_value=FVal(27.20437801956394))  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0xFd83CCCecef02a334e6A86e7eA8D0aa0F61f1Faf']])
def test_pendle_locked_balances(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
        inquirer_defi: 'Inquirer',  # pylint: disable=unused-argument
) -> None:
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xc8b252de1a62daa57d4fe294f371e67550e087fdeffe972261e1acc890d84bd5'),
    )
    protocol_balances_inquirer = PendleBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    )
    protocol_balances = protocol_balances_inquirer.query_balances()
    user_balance = protocol_balances[ethereum_accounts[0]]
    assert user_balance.assets[PENDLE_TOKEN][CPT_PENDLE] == Balance(
        amount=FVal('135.60210839446895642'),
        usd_value=FVal('329.5131233985595641006'),
    )
