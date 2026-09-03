import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.chain.evm.decoding.flying_tulip.put.constants import (
    FLYING_TULIP_PUT_DEPLOYMENTS,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, Location, TimestampMS, deserialize_evm_tx_hash

A_FT = Asset('eip155:1/erc20:0x5DD1A7A369e8273371d2DBf9d83356057088082c')
DEPLOYMENT = FLYING_TULIP_PUT_DEPLOYMENTS[ChainID.ETHEREUM]
PFT_TOKEN = '0xa4215Daaf3745E14E96E169E0E7706c479Ce04F2'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3c9094Fc254371998fE115a6AA38be9955b2f694']])
def test_put_invest(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x2b1ce9db1e985429e3d0103113f64e1aa21145650fcc5944edd03ca0e2430d59')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1771346099000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.001004918305270749'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRANSACTION_TO_SELF,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(0),
            location_label=user_address,
            notes='Transaction to self of 0 ETH',
            address=user_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=613,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_USDT,
            amount=FVal(invest_amount := '25'),
            location_label=user_address,
            notes=f'Set USDT spending approval of {user_address} by {DEPLOYMENT.put_manager} to {invest_amount}',  # noqa: E501
            address=DEPLOYMENT.put_manager,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=614,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal(invest_amount),
            location_label=user_address,
            notes=f'Invest {invest_amount} USDT in Flying Tulip put position #6264',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.put_manager,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=615,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:1/erc721:{PFT_TOKEN}/6264'),
            amount=ONE,
            location_label=user_address,
            notes='Receive the Flying Tulip put position #6264',
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xcdf78fd2195C90f24FE64ddd1426b97BFe62Baa8']])
def test_put_divest(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x490b529dade748ddff0e5a2a312b48d39b4d8592a25b71f67310c95eb0964671')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1786610015000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000720888551342379'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(f'eip155:1/erc721:{PFT_TOKEN}/3891'),
            amount=ONE,
            location_label=user_address,
            notes='Return the Flying Tulip put position #3891',
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDT,
            amount=FVal(divest_amount := '517'),
            location_label=user_address,
            notes=f'Divest {divest_amount} USDT from Flying Tulip put position #3891',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.put_manager,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xaC4AaDC0B865180A408E6C56f4FBDe30c1D078f5']])
def test_put_withdraw_ft(ethereum_inquirer, ethereum_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xd3629ab7a3cb0b7b623ed7d87a1ca0da0218e45796b4f408de52222dc051a702')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1785932483000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000118316863888672'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(f'eip155:1/erc721:{PFT_TOKEN}/671'),
            amount=ONE,
            location_label=user_address,
            notes='Return the Flying Tulip put position #671',
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_FT,
            amount=FVal(ft_amount := '14943.952'),
            location_label=user_address,
            notes=f'Withdraw {ft_amount} FT from Flying Tulip put position #671',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.put_manager,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xE366d92C6fbCAE91FD20E09179AdEbb59FD9BDb6']])
def test_put_invest_via_proxy(ethereum_inquirer, ethereum_accounts):
    """An investment funded through an investing proxy: the user's transfer goes
    to the proxy, which then appears as the investor while the user is the
    position recipient."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf941d701b415cc605ddee5ac76f0af2aaa866b0e453672d987aeb36d0af779ec')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1770161519000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000140340264682185'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDT,
            amount=FVal(invest_amount := '1650'),
            location_label=user_address,
            notes=f'Invest {invest_amount} USDT in Flying Tulip put position #3150',
            counterparty=CPT_FLYING_TULIP,
            address=DEPLOYMENT.put_manager,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:1/erc721:{PFT_TOKEN}/3150'),
            amount=ONE,
            location_label=user_address,
            notes='Receive the Flying Tulip put position #3150',
            counterparty=CPT_FLYING_TULIP,
            address=ZERO_ADDRESS,
        ),
    ]
