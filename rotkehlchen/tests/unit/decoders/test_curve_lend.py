from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.curve.lend.constants import CURVE_LEND_VAULT_SYMBOL
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ARB, A_ETH, A_WBTC, A_WETH_ARB
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_unique_cache_value
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.fixture(name='arbitrum_vault_underlying_token')
def fixture_arbitrum_vault_underlying_token(database: 'DBHandler') -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5'),
        chain_id=ChainID.ARBITRUM_ONE,
        decimals=18,
        symbol='crvUSD',
    )


@pytest.fixture(name='arbitrum_vault_token')
def fixture_arbitrum_vault_token(
        database: 'DBHandler',
        arbitrum_vault_underlying_token: 'EvmToken',
) -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xd3cA9BEc3e681b0f578FD87f20eBCf2B7e0bb739'),
        chain_id=ChainID.ARBITRUM_ONE,
        protocol=CPT_CURVE,
        name='Borrow crvUSD (WETH collateral)',
        symbol=CURVE_LEND_VAULT_SYMBOL,
        underlying_tokens=[UnderlyingToken(
            address=arbitrum_vault_underlying_token.evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


@pytest.fixture(name='arbitrum_vault_token_with_gauge')
def fixture_arbitrum_vault_token_with_gauge(
        database: 'DBHandler',
        globaldb: 'GlobalDBHandler',
) -> 'EvmToken':
    vault_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x0E6Ad128D7E217439bEEa90695FE7ec859c7F98C'),
        chain_id=ChainID.ARBITRUM_ONE,
        protocol=CPT_CURVE,
        name='Curve Vault for crvUSD',
        symbol=CURVE_LEND_VAULT_SYMBOL,
    )
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=[CacheType.CURVE_LENDING_VAULT_GAUGE, vault_token.evm_address],
            value='0x6ba9bF35158dCB0dC9F71CFe1EED9D5c75cd3836',
        )

    return vault_token


@pytest.fixture(name='ethereum_vault_underlying_token')
def fixture_ethereum_vault_underlying_token(database: 'DBHandler') -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
        chain_id=ChainID.ETHEREUM,
        decimals=18,
        symbol='crvUSD',
    )


@pytest.fixture(name='ethereum_vault_token')
def fixture_ethereum_vault_token(
        database: 'DBHandler',
        ethereum_vault_underlying_token: 'EvmToken',
) -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xccd37EB6374Ae5b1f0b85ac97eFf14770e0D0063'),
        chain_id=ChainID.ETHEREUM,
        protocol=CPT_CURVE,
        name='Borrow crvUSD (WBTC collateral)',
        symbol=CURVE_LEND_VAULT_SYMBOL,
        underlying_tokens=[UnderlyingToken(
            address=ethereum_vault_underlying_token.evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


@pytest.fixture(name='optimism_vault_underlying_token')
def fixture_optimism_vault_underlying_token(database: 'DBHandler') -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6'),
        chain_id=ChainID.OPTIMISM,
        decimals=18,
        symbol='crvUSD',
    )


@pytest.fixture(name='optimism_vault_token')
def fixture_optimism_vault_token(
        database: 'DBHandler',
        optimism_vault_underlying_token: 'EvmToken',
) -> 'EvmToken':
    return get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xE8dd743E376EcA40cc9547236D46eD83e06Fd471'),
        chain_id=ChainID.OPTIMISM,
        protocol=CPT_CURVE,
        name='Borrow crvUSD (WETH collateral)',
        symbol=CURVE_LEND_VAULT_SYMBOL,
        underlying_tokens=[UnderlyingToken(
            address=optimism_vault_underlying_token.evm_address,
            token_kind=TokenKind.ERC20,
            weight=ONE,
        )],
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_vault_deposit(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
        arbitrum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xd7e237db5c10970fd4a5a8bccfc87412fad75680d1358a5d39b4a76ba9ffafa6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, approve_amount, deposit_amount, receive_amount = TimestampMS(1732052219000), arbitrum_one_accounts[0], '0.00000265801', '115792089237316195423570985008687907853269984665640564039400.04103445561341153', '57.542973457516228405', '55862.682306216187960829'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=27,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by {arbitrum_vault_token.evm_address} to {approve_amount}',  # noqa: E501
            address=arbitrum_vault_token.evm_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=28,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvUSD in a Curve lending vault',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=arbitrum_vault_token,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} cvcrvUSD after deposit in a Curve lending vault',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4D26f0e78C154f8FDA7AcF6646246Fa135507017']])
def test_vault_withdraw(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
        optimism_vault_token: 'EvmToken',
        optimism_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8f4fe62eebad90a24fd8fb74835dfa3c3cf9d3c38b20ade6425dde54ca98bdd4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, return_amount, withdraw_amount = TimestampMS(1728498363000), optimism_accounts[0], '0.000003575441143222', '99843.76002478005399335', '99.84376024374592538'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=optimism_vault_token,
            amount=FVal(return_amount),
            location_label=user_address,
            notes=f'Return {return_amount} cvcrvUSD to a Curve lending vault',
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=optimism_vault_underlying_token,
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} crvUSD from a Curve lending vault',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x9dba46e6a06FBf24CA11f8912B44338fe1b28Ea9'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1D6702bD3DA0108a4428415FFc74B0efd2F86E4f']])
def test_create_loan(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        ethereum_vault_token: 'EvmToken',
        ethereum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xcaaba5f6206de1a1d3a82a213616548b928397052300057a420ff8083d385b78')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount = TimestampMS(1731831407000), ethereum_accounts[0], '0.004991520607076806', '0.00011219', '6.178023671273738089'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WBTC,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} WBTC as collateral on Curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x8eeDE294459EFaFf55d580bc95C98306Ab03F0C8'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=ethereum_vault_underlying_token,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Borrow {receive_amount} crvUSD from Curve',
            counterparty=CPT_CURVE,
            product=EvmProduct.LENDING,
            address=string_to_evm_address('0xcaD85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617'),
            extra_data={'controller_address': '0xcaD85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF4BD7B061f379ff54Ab54a5A5097A18a93CA8819']])
def test_borrow_more(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        ethereum_vault_token: 'EvmToken',
        ethereum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x6b18af9bf79af5b73a88d6049a4c4e6e67cb6ff43f505b6363e48f3c7aa492ff')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount = TimestampMS(1731312083000), ethereum_accounts[0], '0.005761739463351035', '2', '53000'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=220,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WBTC,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} WBTC as collateral on Curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x8eeDE294459EFaFf55d580bc95C98306Ab03F0C8'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=221,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=ethereum_vault_underlying_token,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Borrow {receive_amount} crvUSD from Curve',
            counterparty=CPT_CURVE,
            product=EvmProduct.LENDING,
            address=string_to_evm_address('0xcaD85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617'),
            extra_data={'controller_address': '0xcaD85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc452b963254a1d1794e0C1ebf0460d79C02e4276']])
def test_create_leveraged_position_with_collateral_asset(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        ethereum_vault_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x94b703880541dd23c4d0d76b3d5bb4ed36e97e5ef7c164fcc8ec081395953699')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount = TimestampMS(1730919179000), ethereum_accounts[0], '0.014631358400811703', '0.72'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=302,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WBTC,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} WBTC into a leveraged Curve position',
            counterparty=CPT_CURVE,
            product=EvmProduct.LENDING,
            address=string_to_evm_address('0x8eeDE294459EFaFf55d580bc95C98306Ab03F0C8'),
            extra_data={'controller_address': '0xcaD85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x59C5B1298DC6Fa9da6d9a911352336e1d879D0C8']])
def test_create_leveraged_position_with_borrowed_asset(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
        arbitrum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x609e8b1b6cf5465441b6d7093b3429b6f8b3c19e0f73c45c8b8f66a47fa9f1bd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, deposit_amount, approve_amount = TimestampMS(1732282256000), arbitrum_one_accounts[0], '0.000812275832834', '3246.108076837089130632', '115792089237316195423570985008687907853269984665640563990215.977712874902778703'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} crvUSD into a leveraged Curve position',
            counterparty=CPT_CURVE,
            product=EvmProduct.LENDING,
            address=string_to_evm_address('0x61C404B60ee9c5fB09F70F9A645DD38fE5b3A956'),
            extra_data={'controller_address': '0xB5c6082d3307088C98dA8D79991501E113e6365d'},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=37,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by 0x61C404B60ee9c5fB09F70F9A645DD38fE5b3A956 to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0x61C404B60ee9c5fB09F70F9A645DD38fE5b3A956'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x36B0aF26728b88BcCDa7d22Be24C21ea560E901F']])
def test_partially_repay_loan(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
        arbitrum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xec6ea0854141775c7adaf90e5e29c7f34574d3725411f7fe2d354505bb2377ac')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, repay_amount, approve_amount = TimestampMS(1732021665000), arbitrum_one_accounts[0], '0.00000807639', '75.812999322471416588', '115792089237316195423570985008687907853269984665640564038872.139121074632427607'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(repay_amount),
            location_label=user_address,
            notes=f'Repay {repay_amount} crvUSD to Curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by 0xB5c6082d3307088C98dA8D79991501E113e6365d to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_close_loan_using_collateral(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
        arbitrum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xcca62e6832e2df6f4ff3ca5240069e2d4548dfd23ed8f08c448e4917b916d3df')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, receive1_amount, receive2_amount = TimestampMS(1732139413000), arbitrum_one_accounts[0], '0.00000751744', '0.311352637896780974', '0.009899999999999997'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(receive1_amount),
            location_label=user_address,
            notes=f'Withdraw {receive1_amount} crvUSD from Curve after repaying loan',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH_ARB,
            amount=FVal(receive2_amount),
            location_label=user_address,
            notes=f'Withdraw {receive2_amount} WETH from Curve after repaying loan',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x61C404B60ee9c5fB09F70F9A645DD38fE5b3A956'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x13cbd624Af484c4C695ff0E1d0B7e125d45F2C76']])
def test_close_loan_using_borrowed(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
        arbitrum_vault_underlying_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x34443f7d317affc6bd2c05207f1ff57b29a15039f7bdc0442feb53e279ba81b2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, repay_amount, receive_amount, approve_amount = TimestampMS(1731958927000), arbitrum_one_accounts[0], '0.000008437093425', '0.001195651117770074', '0.450001578098145238', '115792089237316195423570985008687907853269984665640564036198.434455739459094936'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(repay_amount),
            location_label=user_address,
            notes=f'Repay {repay_amount} crvUSD to Curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH_ARB,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Withdraw {receive_amount} WETH from Curve after repaying loan',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x57126764Dec272132244a10894Ef9bF7B4EE282f'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=arbitrum_vault_underlying_token,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set crvUSD spending approval of {user_address} by 0xB5c6082d3307088C98dA8D79991501E113e6365d to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x13cbd624Af484c4C695ff0E1d0B7e125d45F2C76']])
def test_remove_collateral(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x9798a5e29c83428b79279202514cc61137c04f3fe2150ab36cf4c767a0fb5aab')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, receive_amount = TimestampMS(1731862176000), arbitrum_one_accounts[0], '0.00000584546', '0.1'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH_ARB,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Withdraw {receive_amount} WETH from Curve loan collateral',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x57126764Dec272132244a10894Ef9bF7B4EE282f'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x8228DFbAE77037A5662957Ec8c2111276cF48e92']])
def test_add_collateral(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8090a4ac2314e1700ea6e77d480a2cb576722110febb6a9ea321df7ae7a2988d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, deposit_amount, approve_amount = TimestampMS(1731700246000), arbitrum_one_accounts[0], '0.00000464924', '0.022629905446385494', '115792089237316195423570985008687907853269984665640564039456.319129670009705311'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH_ARB,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} WETH as collateral on Curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x57126764Dec272132244a10894Ef9bF7B4EE282f'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_WETH_ARB,
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set WETH spending approval of {user_address} by 0xB5c6082d3307088C98dA8D79991501E113e6365d to {approve_amount}',  # noqa: E501
            address=string_to_evm_address('0xB5c6082d3307088C98dA8D79991501E113e6365d'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xb84212f378bfb4C552899F2580a2b43a9241b651']])
def test_deposit_into_lending_vault_gauge(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token_with_gauge: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x547aa41360bb39e32e14d4d70bf2a2285635d6c9306549f5e62fbaa355500f9e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, deposit_and_receive_amount = TimestampMS(1741528686000), arbitrum_one_accounts[0], '0.000004084593092', '35147690.896605748325841967'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x0E6Ad128D7E217439bEEa90695FE7ec859c7F98C'),
            amount=FVal(deposit_and_receive_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_and_receive_amount} cvcrvUSD into cvcrvUSD-gauge',
            counterparty=CPT_CURVE,
            product=EvmProduct.GAUGE,
            address=string_to_evm_address('0x6ba9bF35158dCB0dC9F71CFe1EED9D5c75cd3836'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x6ba9bF35158dCB0dC9F71CFe1EED9D5c75cd3836'),
            amount=FVal(deposit_and_receive_amount),
            location_label=user_address,
            counterparty=CPT_CURVE,
            notes=f'Receive {deposit_and_receive_amount} cvcrvUSD-gauge after depositing in curve lending vault gauge',  # noqa: E501
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x7e1E1c5ac70038a9718431C92A618F01f8DADa18']])
def test_withdraw_from_lending_vault_gauge(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token_with_gauge: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xe4e6ce22451a1dbadbb72b99123ce4a04d8b56f63be6fd49f0b6493430bdb772')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, return_and_withdrawn_amount = TimestampMS(1741752784000), arbitrum_one_accounts[0], '0.000005044185033', '95369.61296121579592937'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x6ba9bF35158dCB0dC9F71CFe1EED9D5c75cd3836'),
            amount=FVal(return_and_withdrawn_amount),
            location_label=user_address,
            notes=f'Return {return_and_withdrawn_amount} cvcrvUSD-gauge after withdrawing from curve lending vault gauge',  # noqa: E501
            counterparty=CPT_CURVE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x0E6Ad128D7E217439bEEa90695FE7ec859c7F98C'),
            amount=FVal(return_and_withdrawn_amount),
            location_label=user_address,
            product=EvmProduct.GAUGE,
            counterparty=CPT_CURVE,
            notes=f'Withdraw {return_and_withdrawn_amount} cvcrvUSD from cvcrvUSD-gauge',
            address=string_to_evm_address('0x6ba9bF35158dCB0dC9F71CFe1EED9D5c75cd3836'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xadDD1457C5Fd1a4F2b3161cA614b519b368a3184']])
def test_claim_rewards_from_lending_vault_gauge(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        arbitrum_vault_token_with_gauge: 'EvmToken',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8ada83b9904451335617d625c9f9ba255af193be786149c2914a1f81468d85fe')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, reward_amount = TimestampMS(1740833839000), arbitrum_one_accounts[0], '0.0000008302', '0.037091751198938204'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ARB,
            amount=FVal(reward_amount),
            location_label=user_address,
            notes=f'Receive {reward_amount} ARB rewards from curve lending cvcrvUSD-gauge',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x6ba9bF35158dCB0dC9F71CFe1EED9D5c75cd3836'),
        ),
    ]
