
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LDO, A_USDC, A_USDT, A_WBTC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x93a208b0d7007f5733ea23F65bACF101Be8aC6cD']])
def test_aave_v3_enable_collateral(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x867d09a777ca7c5cbccd281d197ffbed327b5a8f07153483e94f75d4e1d04413')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711029839000)
    deposit_amount, gas_fees = '99503', '0.007154122119159412'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=183,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDT,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} USDT into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=184,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Receive {deposit_amount} aEthUSDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=186,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            balance=Balance(),
            location_label=ethereum_accounts[0],
            notes='Enable USDT as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x203b2E862C57fbAc813c05c46B6e1242844724A2']])
def test_aave_v3_disable_collateral(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1f7614ba2425f3345d02bf1518c81ab3aa46e888553b409f3c9a360259bc7988')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711028735000)
    returned_amount, withdraw_amount, gas_fees = '0.3', '0.30005421', '0.005234272941346752'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=261,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WBTC,
            balance=Balance(),
            location_label=ethereum_accounts[0],
            notes='Disable WBTC as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=262,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
            balance=Balance(amount=FVal(returned_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Return {returned_amount} aEthWBTC to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=263,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WBTC,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {withdraw_amount} WBTC from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x08c14B32C8A48894E4b933090EBcC9CE33B21135']])
def test_aave_v3_deposit(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x062bb6b01d4ac5fabd7b7783965d22589d289e44bb0227bb2fc0adaad7eb563b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711030499000)
    deposit_amount, gas_fees = '71657.177259074315114745', '0.009902467860617334'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=219,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LDO,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} LDO into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x9A44fd41566876A39655f74971a3A6eA0a17a454'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=220,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x9A44fd41566876A39655f74971a3A6eA0a17a454'),  # aWETH
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Receive {deposit_amount} aEthLDO from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xabE9e5d199E1E411098181b6a5Ab9f5f65d91389']])
def test_aave_v3_withdraw(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf184c285dab9ea6c72d18025c65202e3d9e5ec3181209a6cbedf88dfd4c8283f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711030631000)
    return_amount, withdraw_amount, gas_fees = '6770.796829', '6779.85', '0.00692900756596481'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            balance=Balance(amount=FVal(return_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Return {return_amount} aEthUSDT to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDT,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {withdraw_amount} USDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x08c14B32C8A48894E4b933090EBcC9CE33B21135']])
def test_aave_v3_borrow(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x44367976e841cde459d84aec984d5fae4466b2978b1d71c9cd916bb79792ee20')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711030571000)
    borrowed_amount, gas_fees = '79931.500229', '0.011111128567338506'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=217,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
            balance=Balance(amount=FVal(borrowed_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Receive {borrowed_amount} variableDebtEthUSDC from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=221,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_USDC,
            balance=Balance(amount=FVal(borrowed_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Borrow {borrowed_amount} USDC from AAVE v3 with variable APY 13.24%',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9CBF099ff424979439dFBa03F00B5961784c06ce']])
def test_aave_v3_repay(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x440dddaad9f8d9c6d99777494640520854cca8dd102fb557f1654f5746da5f7e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711030643000)
    return_amount, repay_amount, gas_fees = '123942.602894', '123961.452987', '0.00646693553105336'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=158,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
            balance=Balance(amount=FVal(return_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Return {return_amount} variableDebtEthUSDC to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=161,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDC,
            balance=Balance(amount=FVal(repay_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Repay {repay_amount} USDC on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x7420fA58bA44E1141d5E9ADB6903BE549f7cE0b5']])
def test_aave_v3_liquidation(database, ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc1a03e87f1c0446ddd5a77f7eb906831c72618a921a1f6f9f430f612edca0531')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1692320627000)
    payback_amount, liquidation_amount, fee_amount = '23.378156', '0.01887243880551005', '0.000090391508992915'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=242,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WETH,
            balance=Balance(),
            location_label=ethereum_accounts[0],
            notes='Disable WETH as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=243,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
            balance=Balance(amount=FVal(payback_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Payback {payback_amount} variableDebtEthUSDC for an AAVE v3 position',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
            extra_data={'is_liquidation': True},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=247,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=EvmToken('eip155:1/erc20:0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8'),
            balance=Balance(amount=FVal(liquidation_amount)),
            location_label=ethereum_accounts[0],
            notes=f'An AAVE v3 position got liquidated for {liquidation_amount} aEthWETH',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=252,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=EvmToken('eip155:1/erc20:0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8'),
            balance=Balance(amount=FVal(fee_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Spend {fee_amount} aEthWETH as an AAVE v3 fee',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c'),
        ),
    ]
    assert events == expected_events
