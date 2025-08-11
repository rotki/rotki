from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.beefy_finance.constants import CPT_BEEFY_FINANCE
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.morpho.constants import CPT_MORPHO
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_WETH_BASE
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
