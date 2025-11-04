from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.aave.v3.constants import OLD_POOL_ADDRESS
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.decoding.weth.constants import CPT_WETH
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_ETH,
    A_OP,
    A_POL,
    A_USDC,
    A_USDT,
    A_WBNB,
    A_WBTC,
    A_WETH,
    A_WETH_ARB,
    A_XDAI,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.tests.unit.decoders.test_metamask import EvmSwapEvent
from rotkehlchen.tests.unit.decoders.test_paraswap import A_POLYGON_POS_USDC
from rotkehlchen.tests.unit.decoders.test_zerox import A_POLYGON_POS_USDT
from rotkehlchen.tests.utils.constants import A_OPTIMISM_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x93a208b0d7007f5733ea23F65bACF101Be8aC6cD']])
def test_aave_v3_enable_collateral(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x867d09a777ca7c5cbccd281d197ffbed327b5a8f07153483e94f75d4e1d04413')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711029839000)
    deposit_amount, gas_fees = '99503', '0.007154122119159412'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=186,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDT,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Enable USDT as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=187,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} USDT into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=188,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {deposit_amount} aEthUSDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x203b2E862C57fbAc813c05c46B6e1242844724A2']])
def test_aave_v3_disable_collateral(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1f7614ba2425f3345d02bf1518c81ab3aa46e888553b409f3c9a360259bc7988')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711028735000)
    returned_amount, interest_amount, gas_fees = '0.3', '0.00005421', '0.005234272941346752'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=261,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WBTC,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Disable WBTC as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=262,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
            amount=FVal(returned_amount),
            location_label=ethereum_accounts[0],
            notes=f'Return {returned_amount} aEthWBTC to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=263,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WBTC,
            amount=FVal(returned_amount),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {returned_amount} WBTC from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=264,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=A_WBTC,
            amount=FVal(interest_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {interest_amount} WBTC as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x08c14B32C8A48894E4b933090EBcC9CE33B21135']])
def test_aave_v3_deposit(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x062bb6b01d4ac5fabd7b7783965d22589d289e44bb0227bb2fc0adaad7eb563b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711030499000)
    deposit_amount, gas_fees = '71657.177259074315114745', '0.009902467860617334'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'),  # LDO
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} LDO into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x9A44fd41566876A39655f74971a3A6eA0a17a454'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x9A44fd41566876A39655f74971a3A6eA0a17a454'),  # aWETH
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {deposit_amount} aEthLDO from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x8abad97dBdBE16D043a5df66cf9E120D13708a3F']])
def test_aave_v3_deposit_with_interest(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xd5dc3d24da9a97957743c09b8655154ffedb3cb40325b698b1159aa2fe9cf166')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1723640027000)
    deposit_amount, interest_amount, gas_fees = '0.21191208', '0.00000083', '0.000975505588598266'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WBTC,
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} WBTC into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {deposit_amount} aEthWBTC from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=EvmToken('eip155:1/erc20:0x5Ee5bf7ae06D1Be5997A1A72006FE6C607eC6DE8'),
            amount=FVal(interest_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {interest_amount} aEthWBTC as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xabE9e5d199E1E411098181b6a5Ab9f5f65d91389']])
def test_aave_v3_withdraw(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf184c285dab9ea6c72d18025c65202e3d9e5ec3181209a6cbedf88dfd4c8283f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711030631000)
    return_amount, interest_amount, gas_fees = '6770.796829', '9.053171', '0.00692900756596481'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            amount=FVal(return_amount),
            location_label=ethereum_accounts[0],
            notes=f'Return {return_amount} aEthUSDT to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal(return_amount),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {return_amount} USDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=A_USDT,
            amount=FVal(interest_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {interest_amount} USDT as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xa37478676A7A86a6Fb9e8D57D3e543EAc8140A95']])
def test_aave_v3_monerium_order(gnosis_inquirer, gnosis_accounts) -> None:
    """Regression test for https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=129465997

    The reason this happened was that the matching logic was comparing assets and monerium has
    multiple versions of the same asset that are being moved in the same transaction
    """
    tx_hash = deserialize_evm_tx_hash('0x4a8e7cde236b18a4f07e1cd0dbba9e46d3fff75d608a30d6c1db8a5a2b328284')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, return_amount, interest_amount, gas_fees = TimestampMS(1758276410000), '154.130057505168834584', '0.000037471160600675', '0.0000406106'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:100/erc20:0xEdBC7449a9b594CA4E053D9737EC5Dc4CbCcBfb2'),
            amount=FVal(return_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {return_amount} aGnoEURe to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=EvmToken('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(return_amount),
            location_label=gnosis_accounts[0],
            notes=f'Withdraw {return_amount} EURe from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0xEdBC7449a9b594CA4E053D9737EC5Dc4CbCcBfb2'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=EvmToken('eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E'),
            amount=FVal(interest_amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive {interest_amount} EURe as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x430431aE62cD20F0D519ee9fF7E26c2005b50AAf']])
def test_aave_v3_withdraw_with_bigger_interest(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8ed7c1ed348212c6b9aa615a2c13857dd801dfac103f01852a303e62cc58b24f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1723591427000)
    return_amount, interest_amount, gas_fees = '20000', '33086.007538', '0.000395645857253556'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            amount=FVal(return_amount),
            location_label=ethereum_accounts[0],
            notes=f'Return {return_amount} aEthUSDT to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal(return_amount),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {return_amount} USDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            amount=FVal(interest_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {interest_amount} aEthUSDT as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x08c14B32C8A48894E4b933090EBcC9CE33B21135']])
def test_aave_v3_borrow(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x44367976e841cde459d84aec984d5fae4466b2978b1d71c9cd916bb79792ee20')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711030571000)
    borrowed_amount, gas_fees = '79931.500229', '0.011111128567338506'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
            amount=FVal(borrowed_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {borrowed_amount} variableDebtEthUSDC from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_USDC,
            amount=FVal(borrowed_amount),
            location_label=ethereum_accounts[0],
            notes=f'Borrow {borrowed_amount} USDC from AAVE v3 with variable APY 13.24%',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9CBF099ff424979439dFBa03F00B5961784c06ce']])
def test_aave_v3_repay(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x440dddaad9f8d9c6d99777494640520854cca8dd102fb557f1654f5746da5f7e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711030643000)
    return_amount, repay_amount, gas_fees = '123942.602894', '123961.452987', '0.00646693553105336'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
            amount=FVal(return_amount),
            location_label=ethereum_accounts[0],
            notes=f'Return {return_amount} variableDebtEthUSDC to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDC,
            amount=FVal(repay_amount),
            location_label=ethereum_accounts[0],
            notes=f'Repay {repay_amount} USDC on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7420fA58bA44E1141d5E9ADB6903BE549f7cE0b5']])
def test_aave_v3_liquidation(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc1a03e87f1c0446ddd5a77f7eb906831c72618a921a1f6f9f430f612edca0531')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1692320627000)
    payback_amount, liquidation_amount, fee_amount = '23.378156', '0.01887243880551005', '0.000090391508992915'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=242,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Disable WETH as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=243,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004'),
            amount=FVal(payback_amount),
            location_label=ethereum_accounts[0],
            notes=f'Payback {payback_amount} variableDebtEthUSDC for an AAVE v3 position',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
            extra_data={'is_liquidation': True},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=247,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.LOSS,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=EvmToken('eip155:1/erc20:0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8'),
            amount=FVal(liquidation_amount),
            location_label=ethereum_accounts[0],
            notes=f'An AAVE v3 position got liquidated for {liquidation_amount} aEthWETH',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=252,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=EvmToken('eip155:1/erc20:0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8'),
            amount=FVal(fee_amount),
            location_label=ethereum_accounts[0],
            notes=f'Spend {fee_amount} aEthWETH as an AAVE v3 fee',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xA55EaD17fa903b1218dc6a79c47b54C9370E20AB']])
def test_aave_v3_enable_collateral_polygon(polygon_pos_inquirer, polygon_pos_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8002f1a3044bcdec645d512713724f09551c18a14c67509417c83961b230294b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711448176000)
    deposit_amount, gas_fees = '1245.829008', '0.010974492076211867'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=574,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_POLYGON_POS_USDC,
            amount=ZERO,
            location_label=polygon_pos_accounts[0],
            notes='Enable USDC as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=OLD_POOL_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=575,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_POLYGON_POS_USDC,
            amount=FVal(deposit_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Deposit {deposit_amount} USDC into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0xA4D94019934D8333Ef880ABFFbF2FDd611C762BD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=576,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:137/erc20:0xA4D94019934D8333Ef880ABFFbF2FDd611C762BD'),
            amount=FVal(deposit_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {deposit_amount} aPolUSDCn from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x645C22593c232Ae78a7eCbaC93b38cbaC535ef12']])
def test_aave_v3_withdraw_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x09d5e6da511fb88e8a7db6f1209542610a9d3873048e405b88c7a766d7210d6f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711450245000)
    interest_amount, withdraw_amount, gas_fees = '0.094251900832430913', '11.905748099167569087', '0.00000490517'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x191c10Aa4AF7C30e871E70C95dB0E4eb77237530'),
            amount=FVal(withdraw_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Return {withdraw_amount} aArbLINK to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xf97f4df75117a78c1A5a0DBb814Af92458539FB4'),
            amount=FVal(withdraw_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Withdraw {withdraw_amount} LINK from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x191c10Aa4AF7C30e871E70C95dB0E4eb77237530'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=Asset('eip155:42161/erc20:0xf97f4df75117a78c1A5a0DBb814Af92458539FB4'),
            amount=FVal(interest_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {interest_amount} LINK as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xaafc3e3C8B4fD93584256E6D49a9C364648E66cE']])
def test_aave_v3_borrow_base(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x92b6fef0623a3f56daa651968819f2e5b7a982037c19fed2166e4c00ba4d6350')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711452273000)
    borrowed_amount, gas_fees = '0.181', '0.000090985761072991'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=base_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:8453/erc20:0x41A7C3f5904ad176dACbb1D99101F59ef0811DC1'),
            amount=FVal(borrowed_amount),
            location_label=base_accounts[0],
            notes=f'Receive {borrowed_amount} variableDebtBaswstETH from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=EvmToken('eip155:8453/erc20:0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452'),
            amount=FVal(borrowed_amount),
            location_label=base_accounts[0],
            notes=f'Borrow {borrowed_amount} wstETH from AAVE v3 with variable APY 0.30%',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x99CBC45ea5bb7eF3a5BC08FB1B7E56bB2442Ef0D'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x91ed7A7fd3072885c1ec905C932717Df6A8aE2cA']])
def test_aave_v3_withdraw_gnosis(gnosis_inquirer, gnosis_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1f3cae37be928563d154c534c98f41eefe9201eb3d0129c99c1ecb51f83e5596')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711453785000)
    withdraw_amount, gas_fees = '4300', '0.000876816'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:100/erc20:0x7a5c3860a77a8DC1b225BD46d0fb2ac1C6D191BC'),
            amount=FVal(withdraw_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {withdraw_amount} aGnosDAI to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=EvmToken('eip155:100/erc20:0xaf204776c7245bF4147c2612BF6e5972Ee483701'),
            amount=FVal(withdraw_amount),
            location_label=gnosis_accounts[0],
            notes=f'Withdraw {withdraw_amount} sDAI from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x7a5c3860a77a8DC1b225BD46d0fb2ac1C6D191BC'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xdbD5D31B7f48adC13A0aB0c591F7e3D4f9642e69']])
def test_aave_v3_borrow_optimism(optimism_inquirer, optimism_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb043a7f28cccd6cb0392db47cea4607f8cf3b91b6510669a0a62588b66eb7fcf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711455941000)
    borrowed_amount, gas_fees = '2000', '0.000018093759776472'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:10/erc20:0xfb00AC187a8Eb5AFAE4eACE434F493Eb62672df7'),
            amount=FVal(borrowed_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {borrowed_amount} variableDebtOptUSDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_OPTIMISM_USDT,
            amount=FVal(borrowed_amount),
            location_label=optimism_accounts[0],
            notes=f'Borrow {borrowed_amount} USDT from AAVE v3 with variable APY 13.71%',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x6ab707Aca953eDAeFBc4fD23bA73294241490620'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x3E6B4598E5bfeEc911f344E546C9EbFe4A00d770']])
def test_aave_v3_repay_scroll(scroll_inquirer, scroll_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x66010f353be60adaa004f839d37cecd22c35c580060eeaffb9a28ebe169e1692')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1711456958000)
    return_amount, repay_amount, gas_fees = '14459.999417', '14460.008663', '0.000386215421959661'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=scroll_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:534352/erc20:0x3d2E209af5BFa79297C88D6b57F89d792F6E28EE'),
            amount=FVal(return_amount),
            location_label=scroll_accounts[0],
            notes=f'Return {return_amount} variableDebtScrUSDC to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),
            amount=FVal(repay_amount),
            location_label=scroll_accounts[0],
            notes=f'Repay {repay_amount} USDC on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x1D738a3436A8C49CefFbaB7fbF04B660fb528CbD'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x35E0091D67B5e213db857F605c2047cA29A8800d']])
def test_non_aave_tx(ethereum_inquirer, ethereum_accounts) -> None:
    """Test that the non-aave transactions happened through flash loans are not decoded
    as aave events."""
    tx_hash = deserialize_evm_tx_hash('0xf5b4c6f3b4e5bce1f91f7e7eab6185b6d1518e63dea637c79d7f1bbb97edda67')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, multisig, gas_fees = TimestampMS(1713496487000), '0x35542F2c7D18716401A38cc7f08Bf5Bf61f371cc', '0.018530645755598298'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=352,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Successfully executed safe transaction 0x69e95bb0e8452641e165a7cf2f2fa83afb5dc6a6a576bd6e0bc36094df5cc27c for multisig {multisig}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=string_to_evm_address(multisig),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xfB9922C154aF5131C341d537d07e1068368bf3F1',
    '0xD99697546891EE4C20b9A3C65fBfbC356353BEFB',
]])
def test_safe_interaction_interest(ethereum_inquirer, ethereum_accounts) -> None:
    """Test that safe interactions with aave v3 also display interest.
    Regression test for aave post decoding not firing."""
    tx_hash = deserialize_evm_tx_hash('0x01ac87a1fe87913f54153a85f9657359387b82f374cb81132f5ccb30b3bddfbb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, signer, multisig, gas_fees, deposit_amount, interest_amount = TimestampMS(1736015087000), ethereum_accounts[0], ethereum_accounts[1], '0.00184223005590466', '8000', '0.534728'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=signer,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=150,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Successfully executed safe transaction 0x2dcf5b7be25bd993ca1dfe4cce66226a081b59e8e3f1b5e9f808ad7ec210f326 for multisig {multisig}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=string_to_evm_address(multisig),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=151,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal(deposit_amount),
            location_label=multisig,
            notes=f'Deposit {deposit_amount} USDC into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=152,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),  # aEthUSDC  # noqa: E501
            amount=FVal(deposit_amount),
            location_label=multisig,
            notes=f'Receive {deposit_amount} aEthUSDC from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=153,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=EvmToken('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),  # aEthUSDC  # noqa: E501
            amount=FVal(interest_amount),
            location_label=multisig,
            notes=f'Receive {interest_amount} aEthUSDC as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_claim_incentives_reward(optimism_inquirer, optimism_accounts) -> None:
    """Test that claim rewards for incentives works"""
    tx_hash = deserialize_evm_tx_hash('0xa2860ca34ea7558240c44f3d0895a9cf832bd0dd952b2b27d3ae34ba6d45697c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, gas, user, amount = TimestampMS(1666883965000), '0.000198192753532852', optimism_accounts[0], '558.228460248737908186'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_OP,
            amount=FVal(amount),
            location_label=user,
            notes=f'Claim {amount} OP from AAVE v3 incentives',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x929EC64c34a17401F460460D4B9390518E5B473e'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xfe46dCeb5d586DA13aBAA571613e20f5a61fa62e']])
def test_aave_v3_events_with_approval(polygon_pos_inquirer, polygon_pos_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x0aaca18a7e0ee29a247bd9bfab3b081acf469833105a9204251c5a4969a5fc29')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, deposit_amount, approval_amount, gas_fees = TimestampMS(1718134876000), '72.227367', '115792089237316195423570985008687907853269984665640564039457584007903019.443007', '0.006703085584530904'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=142,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_POLYGON_POS_USDT,
            amount=FVal(approval_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Set USDT spending approval of {polygon_pos_accounts[0]} by 0x794a61358D6845594F94dc1DB02A252b5b4814aD to {approval_amount}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=145,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_POLYGON_POS_USDT,
            amount=ZERO,
            location_label=polygon_pos_accounts[0],
            notes='Enable USDT as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=146,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_POLYGON_POS_USDT,
            amount=FVal(deposit_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Deposit {deposit_amount} USDT into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x6ab707Aca953eDAeFBc4fD23bA73294241490620'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=147,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:137/erc20:0x6ab707Aca953eDAeFBc4fD23bA73294241490620'),  # aPolUSDT  # noqa: E501
            amount=FVal(deposit_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {deposit_amount} aPolUSDT from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x76111D2841b41B15e6F07fBae4796a82438D9c90']])
def test_aave_v3_withdraw_eth(scroll_inquirer, scroll_accounts) -> None:
    """Test that withdrawing ETH from Aave gets decoded properly"""
    tx_hash = deserialize_evm_tx_hash('0x65cd06fd54a10052c3d9084d14d28c06e2bb328b1ec39730fab9284cb529d068')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    timestamp, gained_amount, withdrawn_amount, gas_fees = TimestampMS(1716738746000), '0.000000021776581852', '0.010000021776581852', '0.000058164147479909'  # noqa: E501
    weth_gateway = string_to_evm_address('0xFF75A4B698E3Ec95E608ac0f22A03B8368E05F5D')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=scroll_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=58,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:534352/erc20:0xf301805bE1Df81102C957f6d4Ce29d2B8c056B2a'),
            amount=FVal('115792089237316195423570985008687907853269984665640564039457.574007891353058083'),
            location_label=scroll_accounts[0],
            notes='Set aScrWETH spending approval of 0x76111D2841b41B15e6F07fBae4796a82438D9c90 by 0xFF75A4B698E3Ec95E608ac0f22A03B8368E05F5D to 115792089237316195423570985008687907853269984665640564039457.574007891353058083',  # noqa: E501
            counterparty=None,
            address=weth_gateway,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=62,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:534352/erc20:0x5300000000000000000000000000000000000004'),
            amount=ZERO,
            location_label=scroll_accounts[0],
            notes='Disable WETH as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=weth_gateway,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=63,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:534352/erc20:0xf301805bE1Df81102C957f6d4Ce29d2B8c056B2a'),
            amount=FVal(withdrawn_amount),
            location_label=scroll_accounts[0],
            notes=f'Return {withdrawn_amount} aScrWETH to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=weth_gateway,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=64,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(withdrawn_amount),
            location_label=scroll_accounts[0],
            notes=f'Withdraw {withdrawn_amount} ETH from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=weth_gateway,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=65,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=EvmToken('eip155:534352/erc20:0xf301805bE1Df81102C957f6d4Ce29d2B8c056B2a'),
            amount=FVal(gained_amount),
            location_label=scroll_accounts[0],
            notes=f'Receive {gained_amount} aScrWETH as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_arbitrum_deposit_eth_gatewayv3(arbitrum_one_inquirer, arbitrum_one_accounts) -> None:
    """Test that deposit ETH in Aave in Arbitrum gets decoded properly when using gateway v3"""
    tx_hash = deserialize_evm_tx_hash('0xc951183a146d91b996d36632fc8dbe994378da8af88d3c63631a14fcf2f16ca4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1745789183000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := FVal('0.00000215106')),
            location_label=(user := arbitrum_one_accounts[0]),
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:42161/erc20:0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'),  # weth  # noqa: E501
            amount=ZERO,
            location_label=user,
            notes='Enable WETH as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=(weth_gateway := string_to_evm_address('0x5283BEcEd7ADF6D003225C13896E536f2D4264FF')),  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=(amount := FVal('1.59584956103024626')),
            location_label=user,
            notes=f'Deposit {amount} ETH into AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=weth_gateway,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:42161/erc20:0xe50fA9b3c56FfB159cB0FCA61F5c9D750e8128c8'),  # aArbWETH  # noqa: E501
            amount=FVal(amount),
            location_label=user,
            notes=f'Receive {amount} aArbWETH from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x2013b74bdbd2Adf3eBF39E5112a9f794144Aeb15']])
def test_aave_v3_withdraw_matic(polygon_pos_inquirer, polygon_pos_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x301885bdc8998d0e6d5c0064b3b92f5ee34f81ebbd14ca2b796579981ff8df31')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gained_amount, withdrawn_amount, gas_fees, gateway_address, approval_amount = TimestampMS(1720447017000), '0.94342753415979831', '4000', '0.013616476612010713', string_to_evm_address('0xC1E320966c485ebF2A0A2A6d3c0Dc860A156eB1B'), FVal('115792089237316195423570985008687907853269984665640564032456.584007913129639935')  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1223,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:137/erc20:0x6d80113e533a2C0fe82EaBD35f1875DcEA89Ea97'),
            amount=FVal(approval_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Set aPolWMATIC spending approval of {polygon_pos_accounts[0]} by 0xC1E320966c485ebF2A0A2A6d3c0Dc860A156eB1B to {approval_amount}',  # noqa: E501
            tx_ref=tx_hash,
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1224,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:137/erc20:0x6d80113e533a2C0fe82EaBD35f1875DcEA89Ea97'),
            amount=FVal(withdrawn_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Return {withdrawn_amount} aPolWMATIC to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1225,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_POL,
            amount=FVal(withdrawn_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Withdraw {withdrawn_amount} POL from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1226,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=Asset('eip155:137/erc20:0x6d80113e533a2C0fe82EaBD35f1875DcEA89Ea97'),
            amount=FVal(gained_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {gained_amount} aPolWMATIC as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x44ddBB35CfeBbafE98e402970517b33d8e925eB3']])
def test_aave_v3_withdraw_xdai(gnosis_inquirer, gnosis_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x0154ef3042e93a632d654c86bff99f7d452681dba72f4f773806c9c26470f678')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, gained_amount, withdrawn_amount, gas_fees, gateway_address, approval_amount = TimestampMS(1720459795000), '0.076355892637370336', '5.076355892637370336', '0.0008300288', string_to_evm_address('0xfE76366A986B72c3f2923e05E6ba07b7de5401e4'), FVal('115792089237316195423570985008687907853269984665640564039452.507652020492269599')  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:100/erc20:0xd0Dd6cEF72143E22cCED4867eb0d5F2328715533'),
            amount=FVal(approval_amount),
            location_label=gnosis_accounts[0],
            notes=f'Set aGnoWXDAI spending approval of {gnosis_accounts[0]} by 0xfE76366A986B72c3f2923e05E6ba07b7de5401e4 to {approval_amount}',  # noqa: E501
            tx_ref=tx_hash,
            address=gateway_address,
        ), EvmEvent(
            sequence_index=6,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:100/erc20:0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d'),
            amount=ZERO,
            location_label=gnosis_accounts[0],
            notes='Disable WXDAI as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            tx_ref=tx_hash,
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=7,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:100/erc20:0xd0Dd6cEF72143E22cCED4867eb0d5F2328715533'),
            amount=FVal(withdrawn_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {withdrawn_amount} aGnoWXDAI to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=8,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_XDAI,  # aPolUSDT
            amount=FVal(withdrawn_amount),
            location_label=gnosis_accounts[0],
            notes=f'Withdraw {withdrawn_amount} XDAI from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=Asset('eip155:100/erc20:0xd0Dd6cEF72143E22cCED4867eb0d5F2328715533'),
            amount=FVal(gained_amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive {gained_amount} aGnoWXDAI as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x79A4D7448B110bf926d96b726D113f7d7De6781f']])
def test_aave_v3_interest_on_transfer(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x84a70d14ef53987e1ee267435492100f07a4480b7d8022a8d3508e3a4ee70fbf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1723481603000)
    transfer_amount, interest_amount, gas_fees = '50000', '2447.464003', '0.001366713726208557'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=271,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            amount=FVal(interest_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {interest_amount} aEthUSDT as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=273,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x23878914EFE38d27C4D67Ab83ed1b93A74D4086a'),
            amount=FVal(transfer_amount),
            location_label=ethereum_accounts[0],
            notes=f'Send {transfer_amount} aEthUSDT from {ethereum_accounts[0]} to 0x9C9EF79aae8996c72eA8C374011D7ac1eB42c4Fc',  # noqa: E501
            address=string_to_evm_address('0x9C9EF79aae8996c72eA8C374011D7ac1eB42c4Fc'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4F243B4b795502AA5Cf562cB42EccD444c0321b0']])
def test_aave_v3_lido_pool(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xd1e4360f6f7fb34f0f169aeb5e7d0ac0f025e3fed90903a50ee7b1bb694ac8d0')  # noqa: E501
    for address in (
            deserialize_evm_address('0x18577F0f4A0B2Ee6F4048dB51c7acd8699F97DB8'),  # variableDebtEthLidoGHO  # noqa: E501
            deserialize_evm_address('0x18eFE565A5373f430e2F809b97De30335B3ad96A'),  # aEthLidoGHO
    ):
        get_or_create_evm_token(
            evm_inquirer=ethereum_inquirer,
            userdb=ethereum_inquirer.database,
            evm_address=address,
            chain_id=ethereum_inquirer.chain_id,
            protocol=CPT_AAVE_V3,
            token_kind=TokenKind.ERC20,
            underlying_tokens=[UnderlyingToken(
                address=string_to_evm_address('0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f'),
                token_kind=TokenKind.ERC20,
                weight=ONE,
            )],
        )

    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    borrow_amount, gas_fees, timestamp = '59000', '0.00170195956638183', TimestampMS(1734912023000)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x18577F0f4A0B2Ee6F4048dB51c7acd8699F97DB8'),
            amount=FVal(borrow_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {borrow_amount} variableDebtEthLidoGHO from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=EvmToken('eip155:1/erc20:0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f'),
            amount=FVal(borrow_amount),
            location_label=ethereum_accounts[0],
            notes=f'Borrow {borrow_amount} GHO from AAVE v3 with variable APY 10.53%',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x18eFE565A5373f430e2F809b97De30335B3ad96A'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_aave_v3_deposit_bnb(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x07b14d73cf0b4ca453883178c6521a6c6fd21cd7ee2bf7650badc8be61d9c76e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, deposit_amount, gateway_address = binance_sc_accounts[0], TimestampMS(1736455901000), '0.000624072', '0.005', string_to_evm_address('0xe63eAf6DAb1045689BD3a332bC596FfcF54A5C88')  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} BNB for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=23,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WBNB,
        amount=ZERO,
        location_label=user_address,
        notes='Enable WBNB as collateral on AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=gateway_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=24,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_BSC_BNB,
        amount=FVal(deposit_amount),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} BNB into AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=gateway_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=25,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:56/erc20:0x9B00a09492a626678E5A3009982191586C444Df9'),
        amount=FVal(deposit_amount),
        location_label=user_address,
        notes=f'Receive {deposit_amount} aBnbWBNB from AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x57D4bEb0fD4438b8910fEf03a961131742D845E2', '0x1cdC859a9685103A0791075B6c365e2D583BC236']])   # noqa: E501
def test_aave_v3_close_position_with_safe(arbitrum_one_inquirer, arbitrum_one_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x56c57b83508f46d45af6b3230ee882f99df315c089af3250fbe5494ea59e5624')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user_eoa_account, user_safe_proxy, eth_interest_amount, eth_withdraw_amount, usd_paid_back_amount, gas_fees = TimestampMS(1736028280000), arbitrum_one_accounts[0], arbitrum_one_accounts[1], '0.031127570161941882', '3.007038496271076913', '2353.18136', '0.00000658667'  # noqa: E501

    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=user_eoa_account,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(eth_withdraw_amount) + FVal(eth_interest_amount),
            location_label=user_safe_proxy,
            notes=f'Transfer {FVal(eth_withdraw_amount) + FVal(eth_interest_amount)} ETH to {user_eoa_account}',  # noqa: E501
            counterparty=None,
            address=user_eoa_account,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal(usd_paid_back_amount),
            location_label=user_eoa_account,
            notes=f'Transfer {usd_paid_back_amount} USDT from {user_eoa_account} to {user_safe_proxy}',  # noqa: E501
            address=user_safe_proxy,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal('0.234868'),
            location_label=user_eoa_account,
            notes=f'Set USDT spending approval of {user_eoa_account} by {user_safe_proxy} to 0.234868',  # noqa: E501
            address=user_safe_proxy,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=ZERO,
            location_label=user_safe_proxy,
            notes=f'Revoke USDT spending approval of {user_safe_proxy} by 0x794a61358D6845594F94dc1DB02A252b5b4814aD',  # noqa: E501
            address=string_to_evm_address('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=7,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal(usd_paid_back_amount),
            location_label=user_safe_proxy,
            notes=f'Set USDT spending approval of {user_safe_proxy} by 0x794a61358D6845594F94dc1DB02A252b5b4814aD to {usd_paid_back_amount}',   # noqa: E501
            address=string_to_evm_address('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:42161/erc20:0xfb00AC187a8Eb5AFAE4eACE434F493Eb62672df7'),
            amount=FVal('2251.145752'),
            location_label=user_safe_proxy,
            notes=f'Send 2251.145752 variableDebtArbUSDT from {user_safe_proxy} to 0x0000000000000000000000000000000000000000',  # noqa: E501
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal(usd_paid_back_amount),
            location_label=user_safe_proxy,
            notes=f'Repay {usd_paid_back_amount} USDT on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0x6ab707Aca953eDAeFBc4fD23bA73294241490620'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=ZERO,
            location_label=user_safe_proxy,
            notes=f'Revoke USDT spending approval of {user_safe_proxy} by 0x794a61358D6845594F94dc1DB02A252b5b4814aD',  # noqa: E501
            address=string_to_evm_address('0x794a61358D6845594F94dc1DB02A252b5b4814aD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WETH_ARB,
            amount=ZERO,
            location_label=user_safe_proxy,
            notes='Disable WETH as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=user_safe_proxy,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH_ARB,
            amount=(unwrap_amount := FVal(eth_withdraw_amount) + FVal(eth_interest_amount)),
            location_label=user_safe_proxy,
            notes=f'Unwrap {unwrap_amount} WETH',
            counterparty=CPT_WETH,
            address=user_safe_proxy,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=26,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_eoa_account,
            notes=f'Successfully executed safe transaction 0xd7a87c1f11f5cbe9685d1e0627ea5ba8cf7373ec738cb2da4e345b836b67c2ef for multisig {user_safe_proxy}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=user_safe_proxy,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=28,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=unwrap_amount,
            location_label=user_safe_proxy,
            notes=f'Receive {unwrap_amount} ETH',
            counterparty=CPT_WETH,
            address=A_WETH_ARB.resolve_to_evm_token().evm_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:42161/erc20:0xe50fA9b3c56FfB159cB0FCA61F5c9D750e8128c8'),
            amount=FVal(eth_withdraw_amount),
            location_label=user_safe_proxy,
            notes=f'Return {eth_withdraw_amount} aArbWETH to AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=30,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WETH_ARB,
            amount=FVal(eth_withdraw_amount),
            location_label=user_safe_proxy,
            notes=f'Withdraw {eth_withdraw_amount} WETH from AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=string_to_evm_address('0xe50fA9b3c56FfB159cB0FCA61F5c9D750e8128c8'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=31,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.INTEREST,
            asset=A_WETH_ARB,
            amount=FVal(eth_interest_amount),
            location_label=user_safe_proxy,
            notes=f'Receive {eth_interest_amount} WETH as interest earned from AAVE v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x56a1A34F0d33788ebA53e2706854A37A5F275536']])
def test_gnosis_xdai_deposit(gnosis_inquirer, gnosis_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xbdc74d91e713209a666daf25a97da7c73aca646a7e7c0e126954e6a4c644eb72')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1751201820000)),
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(gas_fees := '0.00000001663646463'),
        location_label=(user_address := gnosis_accounts[0]),
        notes=f'Burn {gas_fees} XDAI for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_XDAI,
        amount=FVal(deposit_amount := '1000'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} XDAI into AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0x721B9abAb6511b46b9ee83A1aba23BDAcB004149'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:100/erc20:0xd0Dd6cEF72143E22cCED4867eb0d5F2328715533'),
        amount=FVal(deposit_amount),
        location_label=user_address,
        notes=f'Receive {deposit_amount} aGnoWXDAI from AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.INTEREST,
        asset=Asset('eip155:100/erc20:0xd0Dd6cEF72143E22cCED4867eb0d5F2328715533'),
        amount=FVal(interest_amount := '6.116920794676377147'),
        location_label=user_address,
        notes=f'Receive {interest_amount} aGnoWXDAI as interest earned from AAVE v3',
        counterparty=CPT_AAVE_V3,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xE37b28362F65060C18c16398cFD23275D8CaE750']])
def test_aave_v3_collateral_swap(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xdc1a92c8cbda2fe7917e633efd889d17fc62e88e0f584af65f577b5d2a8bcb3c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755166263000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees := '0.000006714097305863'),
        location_label=base_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1639,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=EvmToken('eip155:8453/erc20:0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7'),
        amount=FVal(approval := '115792089237316195423570985008687907853269984665640564039457.583533021730857741'),  # noqa: E501
        location_label=base_accounts[0],
        notes=f'Set aBasWETH spending approval of 0xE37b28362F65060C18c16398cFD23275D8CaE750 by 0x2E549104c516b8657A7D888494DfbAbD7C70b464 to {approval}',  # noqa: E501
        address=string_to_evm_address('0x2E549104c516b8657A7D888494DfbAbD7C70b464'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1644,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=EvmToken('eip155:8453/erc20:0x4200000000000000000000000000000000000006'),
        amount=ZERO,
        location_label=base_accounts[0],
        notes='Disable WETH as collateral on AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0x2E549104c516b8657A7D888494DfbAbD7C70b464'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1645,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.INTEREST,
        asset=EvmToken('eip155:8453/erc20:0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7'),
        amount=FVal(interest_amount := '0.000000000001857221'),
        location_label=base_accounts[0],
        notes=f'Receive {interest_amount} aBasWETH as interest earned from AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=ZERO_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1646,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=EvmToken('eip155:8453/erc20:0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7'),
        amount=FVal(swapped_amount := '0.000109666465527922'),
        location_label=base_accounts[0],
        notes=f'Swap {swapped_amount} aBasWETH AAVE v3 collateral',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0x2E549104c516b8657A7D888494DfbAbD7C70b464'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1647,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=EvmToken('eip155:8453/erc20:0x99CBC45ea5bb7eF3a5BC08FB1B7E56bB2442Ef0D'),
        amount=FVal(swapped_amount := '0.000090901062973315'),
        location_label=base_accounts[0],
        notes=f'Receive {swapped_amount} aBaswstETH as the result of collateral swap in AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0x2E549104c516b8657A7D888494DfbAbD7C70b464'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0BeBD2FcA9854F657329324aA7dc90F656395189']])
def test_batch_aave3_operations_via_safe(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xcb42b04cf1b8dbc70c21c07f150107a500da4f19753b07a14ffa9b6f84645d33')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=900,
        timestamp=(timestamp := TimestampMS(1757542811000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        amount=ZERO,
        location_label=(user_address := ethereum_accounts[0]),
        notes='Enable WETH as collateral on AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0x9641d764fc13c8B624c04430C7356C1C7C8102e2'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=901,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=(weth_deposit_amount := FVal('0.1')),
        location_label=user_address,
        notes=f'Deposit {weth_deposit_amount} ETH into AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0xd01607c3C5eCABa394D8be377a08590149325722'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=902,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8'),
        amount=(wrapped_aave_weth_amount := FVal('0.099999999999999999')),
        location_label=user_address,
        notes=f'Receive {wrapped_aave_weth_amount} aEthWETH from AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=903,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=(usdc_deposit_amount := FVal('840')),
        location_label=user_address,
        notes=f'Deposit {usdc_deposit_amount} USDC into AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=string_to_evm_address('0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=904,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        amount=(wrapped_aave_usdc_amount := FVal('839.999999')),
        location_label=user_address,
        notes=f'Receive {wrapped_aave_usdc_amount} aEthUSDC from AAVE v3',
        counterparty=CPT_AAVE_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=905,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.INTEREST,
        asset=Asset('eip155:1/erc20:0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c'),
        amount=(interest_amount := FVal('1.581004')),
        location_label=user_address,
        notes=f'Receive {interest_amount} aEthUSDC as interest earned from AAVE v3',
        counterparty=CPT_AAVE_V3,
    )]
    assert events == expected_events
