from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.beefy_finance.constants import CPT_BEEFY_FINANCE
from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_GMX, A_USDC, A_WETH_ARB, A_WETH_BASE
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    FVal,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.fixture(name='beefy_cache')
def _beefy_cache(database: 'DBHandler') -> None:
    """Fixture that preloads beefy finance's vaults."""
    get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x81F040E82aae01f3921A1c1225C86ce5C57C218b'),
        chain_id=ChainID.ETHEREUM,
        name='Moo FxConvex GHO-fxUSD',
        symbol='mooFxConvexGHO-fxUSD',
        decimals=18,
        protocol=CPT_BEEFY_FINANCE,
    )
    get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
        chain_id=ChainID.ETHEREUM,
        name='Moo FxConvex USDC-fxUSD',
        symbol='mooFxConvexUSDC-fxUSD',
        decimals=18,
        protocol=CPT_BEEFY_FINANCE,
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x71b278042bFf0537CbAc1d5cF2197Bd8f4f79EeF']])
def test_zap_deposit_to_beefy(ethereum_inquirer, ethereum_accounts, beefy_cache):
    tx_hash = deserialize_evm_tx_hash('0xab6fab1441b7f6843109eb1c903e93c7d24536d09a81aced724302e1c8002c71')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749354935000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00032154758985688'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := ethereum_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_USDC,
        amount=FVal(deposit_amount := '33500'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} USDC in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0x5Cc9400FfB4Da168Cf271e912F589462C3A00d1F'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
        amount=FVal(receive_amount := '31995.860448954984572623'),
        location_label=user_address,
        notes=f'Receive {receive_amount} mooFxConvexUSDC-fxUSD after depositing in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0x5Cc9400FfB4Da168Cf271e912F589462C3A00d1F'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xfaC2F11ba2577D5122DC1EC5301d35B16688251E']])
def test_zap_withdrawal_from_beefy(ethereum_inquirer, ethereum_accounts, beefy_cache):
    tx_hash = deserialize_evm_tx_hash('0x3dab2b65117b4c3953a20e6d850a7aa1b15351de30382cea31a4dba795ec3101')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749215411000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0009786576'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := ethereum_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=472,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(vault_token := Asset('eip155:1/erc20:0x81F040E82aae01f3921A1c1225C86ce5C57C218b')),
        amount=FVal(approval_amount := '7999998797.708849523052076792'),
        location_label=user_address,
        notes=f'Set mooFxConvexGHO-fxUSD spending approval of {user_address} by 0xEdFEc19ee32f5130084C0aCab91FeA604C137912 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0xEdFEc19ee32f5130084C0aCab91FeA604C137912'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=473,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=vault_token,
        amount=FVal(return_amount := '1202.291150476947923208'),
        location_label=user_address,
        notes=f'Return {return_amount} mooFxConvexGHO-fxUSD to a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0x5Cc9400FfB4Da168Cf271e912F589462C3A00d1F'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=474,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:1/erc20:0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f'),
        amount=FVal(withdrawn_amount := '1512.988532036017891381'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_amount} GHO from a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0x5Cc9400FfB4Da168Cf271e912F589462C3A00d1F'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7B8e047dFa4B27314C6A7EA5067e356F38666089']])
def test_deposit_to_beefy(ethereum_inquirer, ethereum_accounts, beefy_cache):
    tx_hash = deserialize_evm_tx_hash('0x5d11116ca9ff5edc826394f93c7ee81057119899daa0a9a77d384909584d816e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749395555000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0006633802'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := ethereum_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=696,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:1/erc20:0x5018BE882DccE5E3F2f3B0913AE2096B9b3fB61f'),
        amount=FVal(approve_amount := '7999900560.118661539430036479'),
        location_label=user_address,
        notes=f'Set USDCfxUSD spending approval of {user_address} by 0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A to {approve_amount}',  # noqa: E501
        address=string_to_evm_address('0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=697,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0x5018BE882DccE5E3F2f3B0913AE2096B9b3fB61f'),
        amount=FVal(deposit_amount := '99439.881338460569963521'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} USDCfxUSD in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=698,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
        amount=FVal(receive_amount := '95430.115317326331850983'),
        location_label=user_address,
        notes=f'Receive {receive_amount} mooFxConvexUSDC-fxUSD after depositing in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA2d238002Bf1A91fed3C218fA770C4933d833ead']])
def test_withdrawal_from_beefy(ethereum_inquirer, ethereum_accounts, beefy_cache):
    tx_hash = deserialize_evm_tx_hash('0xda0a5066e573451465447a0d84d2b62b14dd980b3df7421c639b1beea9f9ec4a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749106427000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0009627226326753'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := ethereum_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc20:0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
        amount=FVal(return_amount := '12.417673241386034282'),
        location_label=user_address,
        notes=f'Return {return_amount} mooFxConvexUSDC-fxUSD to a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:1/erc20:0x5018BE882DccE5E3F2f3B0913AE2096B9b3fB61f'),
        amount=FVal(withdrawn_amount := '12.921307356779707369'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_amount} USDCfxUSD from a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xD81eaAE8E6195e67695bE9aC447c9D6214CB717A'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0xf5632CFcD668C10949bA06618D50928ce5841aE3']])
def test_deposit_to_beefy_morpho_vault(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test a deposit into a Beefy vault that uses a Morpho vault under the hood.
    Regression test for a problem where the deposit event was decoded as a Morpho deposit instead
    of a Beefy deposit.
    """
    beefy_vault = get_or_create_evm_token(
        userdb=base_inquirer.database,
        evm_address=string_to_evm_address('0x0A2Bc5Bd33bac3C34551C67Af3657451911518Fa'),
        chain_id=ChainID.BASE,
        name='Moo Morpho Seamless WETH',
        symbol='mooMorpho-Seamless-WETH',
        decimals=18,
        protocol=CPT_BEEFY_FINANCE,
    )
    get_or_create_evm_token(
        userdb=base_inquirer.database,
        evm_address=string_to_evm_address('0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18'),
        chain_id=ChainID.BASE,
        symbol='smWETH',
        name='Seamless WETH Vault',
        decimals=18,
        protocol=CPT_MORPHO,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x4200000000000000000000000000000000000006'),
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash('0x9ec67f14375ce96036b23f4b13c38dcee6d74973d4be0ba81c775674450da340')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1754816425000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000003805651040272'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := base_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_WETH_BASE,
        amount=FVal(deposit_amount := '3.31915163308690925'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} WETH in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=beefy_vault.evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x0A2Bc5Bd33bac3C34551C67Af3657451911518Fa'),
        amount=FVal(receive_amount := '3.256100328058877126'),
        location_label=user_address,
        notes=f'Receive {receive_amount} mooMorpho-Seamless-WETH after depositing in a Beefy vault',  # noqa: E501
        counterparty=CPT_BEEFY_FINANCE,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x2006cA9b17cc173B3b76009B8A43f144D7a26C1B']])
def test_withdrawal_from_beefy_clm_vault(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    cow_token = get_or_create_evm_token(
        userdb=arbitrum_one_inquirer.database,
        evm_address=string_to_evm_address('0x78Da75e22e44B0A4DBcA353a4a242eDc5FcB1553'),
        chain_id=ChainID.ARBITRUM_ONE,
        token_kind=TokenKind.ERC20,
        symbol='cowUniswapArbETH-GMX',
        name='Cow Uniswap Arb ETH-GMX',
        decimals=18,
        protocol=CPT_BEEFY_FINANCE,
    )
    rcow_token = get_or_create_evm_token(
        userdb=arbitrum_one_inquirer.database,
        evm_address=string_to_evm_address('0xb936900CEF5C45b2c921e958D75Dc3659980ae0B'),
        chain_id=ChainID.ARBITRUM_ONE,
        token_kind=TokenKind.ERC20,
        symbol='rcowUniswapArbETH-GMX',
        name='Reward Cow Uniswap Arb ETH-GMX',
        decimals=18,
        protocol=CPT_BEEFY_FINANCE,
        underlying_tokens=[UnderlyingToken(
            address=cow_token.evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )
    tx_hash = deserialize_evm_tx_hash('0xc964a5c62d7ce489e8d21d5a222bebbb11fccd802fe250cf66118a17f06e9ee5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1754883188000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0000104133'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := arbitrum_one_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=10,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=rcow_token,
        amount=FVal(approval_amount := '7999999992.60870368519187435'),
        location_label=user_address,
        notes=f'Set rcowUniswapArbETH-GMX spending approval of {user_address} by 0x3395BDAE49853Bc7Ab9377d2A93f42BC3A18680e to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x3395BDAE49853Bc7Ab9377d2A93f42BC3A18680e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=rcow_token,
        amount=FVal(return_amount := '7.39129631480812565'),
        location_label=user_address,
        notes=f'Return {return_amount} rcowUniswapArbETH-GMX to a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_WETH_ARB,
        amount=FVal(withdrawn_weth := '0.046952104934080391'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_weth} WETH from a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_GMX,
        amount=FVal(withdrawn_gmx := '0.055194333850194218'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_gmx} GMX from a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xd67eCd5C445519BDEaE60Fd53541100f5D9f5fB1']])
def test_deposit_eth_to_beefy_vault_with_harvest_call_reward(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x9ade23d1ea48257b13e983d0a542fafbfa1dd195975a94b8d3505ef767527167')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755000647000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00001589032'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := arbitrum_one_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(deposit_amount := '0.23893675137792528'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} ETH in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:42161/erc20:0x764e4e75e3738615CDBFAeaE0C8527b1616e1123'),
        amount=FVal(receive_amount := '0.219166695622906559'),
        location_label=user_address,
        notes=f'Receive {receive_amount} mooAuraArbrsETH-WETH after depositing in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_WETH_ARB,
        amount=FVal(reward_amount := '0.000001355478180152'),
        location_label=user_address,
        notes=f'Receive {reward_amount} WETH as Beefy strategy harvest call reward',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0x498Be1Ff97392073067915A17F56b9913C976958'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x6f04Ee70b9eF46986d12B2f6c544C1Af8B07D433']])
def test_deposit_usdc_to_beefy_vault_with_harvest_call_reward(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """This test differs from the deposit-eth one above in that the charged_fees tx log event
    has the values in the data instead of as log topics.
    """
    tx_hash = deserialize_evm_tx_hash('0x6dc43b963357b6a40adea87129030430d145deb4463d43bec8be324a4e2190e0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755003899000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00010518138396'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := arbitrum_one_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=6,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
        amount=FVal(approval_amount := '7999999999999999999899.789207'),
        location_label=user_address,
        notes=f'Set USDC.e spending approval of {user_address} by 0x3395BDAE49853Bc7Ab9377d2A93f42BC3A18680e to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x3395BDAE49853Bc7Ab9377d2A93f42BC3A18680e'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=7,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
        amount=FVal(deposit_amount := '100.210793'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} USDC.e in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=8,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:42161/erc20:0xb9A27ba529634017b12e3cbbbFFb6dB7908a8C8B'),
        amount=FVal(receive_amount := '0.00000000008793948'),
        location_label=user_address,
        notes=f'Receive {receive_amount} mooCompoundArbUSDC after depositing in a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xf49F7bB6F4F50d272A0914a671895c4384696E5A'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=9,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_WETH_ARB,
        amount=FVal(reward_amount := '0.00000016748016936'),
        location_label=user_address,
        notes=f'Receive {reward_amount} WETH as Beefy strategy harvest call reward',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0x15Ad422c4983113a0d332FF9144beA992d0120f7'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('optimism_accounts', [['0xB012F9199Ea0BbF86F99C2e1A572747fB7B5a953']])
def test_withdrawal_from_beefy_receiving_eth(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that withdrawing ETH from a Beefy vault is decoded correctly. The ETH receive event
    comes before the spend event during decoding and was being decoded incorrectly.
    """
    cow_token = get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0xCF9381a9a363f8614f67323f7E0A1E257A438F73'),
        chain_id=ChainID.OPTIMISM,
        token_kind=TokenKind.ERC20,
        symbol='mooStargateV2WETH',
        name='Moo StargateV2 WETH',
        decimals=18,
        protocol=CPT_BEEFY_FINANCE,
    )
    tx_hash = deserialize_evm_tx_hash('0x1fb86d2bcbccde112422984862ac5ed4f88a2414b86a740ed64ea082b099ee2a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1754903127000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000338654907628'),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        location_label=(user_address := optimism_accounts[0]),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=19,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=cow_token,
        amount=FVal(approval_amount := '7999999997.477672183234260184'),
        location_label=user_address,
        notes=f'Set mooStargateV2WETH spending approval of {user_address} by 0x5a32F67C5eD74dc1b2e031b1bc2c3E965073424F to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x5a32F67C5eD74dc1b2e031b1bc2c3E965073424F'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=20,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=cow_token,
        amount=FVal(return_amount := '2.522327816765739816'),
        location_label=user_address,
        notes=f'Return {return_amount} mooStargateV2WETH to a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xE82343A116d2179F197111D92f9B53611B43C01c'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=21,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(withdrawn_amount := '2.791867'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_amount} ETH from a Beefy vault',
        counterparty=CPT_BEEFY_FINANCE,
        address=string_to_evm_address('0xE82343A116d2179F197111D92f9B53611B43C01c'),
    )]
