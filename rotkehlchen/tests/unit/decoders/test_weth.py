import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.weth.constants import CPT_WETH
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.wxdai.constants import CPT_WXDAI
from rotkehlchen.chain.polygon_pos.modules.wmatic.constants import CPT_WMATIC
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import (
    A_ETH,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_WETH,
    A_WETH_ARB,
    A_WETH_BASE,
    A_WETH_OPT,
    A_WETH_SCROLL,
    A_WMATIC,
    A_WXDAI,
    A_XDAI,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

WETH_OP_BASE_ADDRESS = string_to_evm_address('0x4200000000000000000000000000000000000006')
WMATIC_ADDRESS = string_to_evm_address('0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270')
WETH_SCROLL_ADDRESS = string_to_evm_address('0x5300000000000000000000000000000000000004')
WETH_MAINNET_ADDRESS = string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
WETH_ARB_ADDRESS = string_to_evm_address('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd']])
def test_weth_deposit(ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf
    """
    tx_hash = deserialize_evm_tx_hash('0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf')  # noqa: E501
    timestamp = TimestampMS(1666256147000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00057313513694104'),
            location_label='0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd',
            notes='Burn 0.00057313513694104 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(0.06),
            location_label='0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd',
            notes='Wrap 0.06 ETH in WETH',
            counterparty=CPT_WETH,
            address=WETH_MAINNET_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WETH,
            amount=FVal(0.06),
            location_label='0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd',
            notes='Receive 0.06 WETH',
            counterparty=CPT_WETH,
            address=WETH_MAINNET_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3']])
def test_weth_withdrawal(ethereum_inquirer):
    """
    Data for withdrawal is taken from
    https://etherscan.io/tx/0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07
    """
    tx_hash = deserialize_evm_tx_hash('0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07')  # noqa: E501
    timestamp = TimestampMS(1666256147000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00062372398538032'),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Burn 0.00062372398538032 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH,
            amount=FVal(0.5),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Unwrap 0.5 WETH',
            counterparty=CPT_WETH,
            address=WETH_MAINNET_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(0.5),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Receive 0.5 ETH',
            counterparty=CPT_WETH,
            address=WETH_MAINNET_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xC4DdFf531132d32b47eC938AcfA28E354769A806']])
def test_weth_interaction_with_protocols_deposit(database, ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9
    """
    tx_hash = deserialize_evm_tx_hash('0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9')  # noqa: E501
    timestamp = TimestampMS(1666595591000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert len(events) == 4
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.004777703202235758'),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Burn 0.004777703202235758 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal('0.999999999949533767'),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Deposit 0.999999999949533767 ETH to Uniswap V3 LP 343053',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal('294.145955'),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Deposit 294.145955 USDC to Uniswap V3 LP 343053',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc721:0xC36442b4a4522E871399CD717aBDD847Ab11FE88/343053'),
            amount=ONE,
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Create Uniswap V3 LP with id 343053',
            counterparty=CPT_UNISWAP_V3,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47']])
def test_weth_interaction_with_protocols_withdrawal(ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167
    """
    tx_hash = deserialize_evm_tx_hash('0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167')  # noqa: E501
    timesatmp = TimestampMS(1666284551000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timesatmp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.011940359686863452'),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Burn 0.011940359686863452 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=deserialize_evm_tx_hash(
                '0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167',
            ),
            sequence_index=1,
            timestamp=timesatmp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal('0.764522981784947382'),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Remove 0.764522981784947382 ETH from Uniswap V3 LP 337559',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timesatmp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            amount=FVal('1028.82092'),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Remove 1028.82092 USDC from Uniswap V3 LP 337559',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d']])
def test_weth_interaction_errors(ethereum_inquirer):
    """
    Check that if no out event occurs, an in event should not be created for deposit event
    https://etherscan.io/tx/0x4ca19c97b7533e74f36dff18acf0115055f63f9d8ae078dfc8ab15ceb14d2f2d
    """
    tx_hash = deserialize_evm_tx_hash('0x4ca19c97b7533e74f36dff18acf0115055f63f9d8ae078dfc8ab15ceb14d2f2d')  # noqa: E501
    timestamp = TimestampMS(1666800983000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.003535483550478045),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Burn 0.003535483550478045 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(0.06693824468797216),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Send 0.06693824468797216 ETH to 0xe66B31678d6C16E9ebf358268a790B763C133750',
            address=string_to_evm_address('0xe66B31678d6C16E9ebf358268a790B763C133750'),
        ), EvmEvent(
            tx_hash=tx_hash,
            timestamp=timestamp,
            sequence_index=181,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC,
            amount=FVal(103.562282),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Receive 103.562282 USDC from 0xe66B31678d6C16E9ebf358268a790B763C133750 to 0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',  # noqa: E501
            address=string_to_evm_address('0xe66B31678d6C16E9ebf358268a790B763C133750'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_wxdai_unwrap(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xa6af9ea737de26c87a36367fd896a8fe471049f4c18ac909901336aaccbf2369')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1707739650000)
    gas_amount, unwrapped_amount = '0.0000886822502438', '555.374747825771664891'
    wxdai_address = A_WXDAI.resolve_to_evm_token().evm_address
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WXDAI,
            amount=FVal(unwrapped_amount),
            location_label=user_address,
            notes=f'Unwrap {unwrapped_amount} WXDAI',
            counterparty=CPT_WXDAI,
            address=wxdai_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_XDAI,
            amount=FVal(unwrapped_amount),
            location_label=user_address,
            notes=f'Receive {unwrapped_amount} XDAI',
            counterparty=CPT_WXDAI,
            address=wxdai_address,
        ),
    ]

    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0xd6f585378F3232E440B165AD56658bFcA76D1B32']])
def test_wxdai_wrap(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x8cf8362f36e5a76912bc05ef804c0ea4b4f2de54700afe9ced99aa486f3dd0e8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1707744465000)
    gas_amount, wrapped_amount = '0.0000586761', '103'
    wxdai_address = A_WXDAI.resolve_to_evm_token().evm_address
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_XDAI,
            amount=FVal(wrapped_amount),
            location_label=user_address,
            notes=f'Wrap {wrapped_amount} XDAI in WXDAI',
            counterparty=CPT_WXDAI,
            address=wxdai_address,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WXDAI,
            amount=FVal(wrapped_amount),
            location_label=user_address,
            notes=f'Receive {wrapped_amount} WXDAI',
            counterparty=CPT_WXDAI,
            address=wxdai_address,
        ),
    ]

    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xBE6660FBE96B61B72Bf35FFaB40eB2CA886A7f85']])
def test_weth_withdraw_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc19c7e1e0af7819b1922a287d034540e8f8dba4e065317d6483d48ac27e727e9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712238368000)
    amount, gas_fees = '0.00052', '0.00000108547'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH_ARB,
            amount=FVal(amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Unwrap {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_ARB_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {amount} ETH',
            counterparty=CPT_WETH,
            address=WETH_ARB_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x7aBAee8F04EFd689961115f7A28bAA2E73Be6703']])
def test_weth_deposit_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x57cc837c6f3d84c8fa3db8a7405f7244f11d32152159edf5ba79f5a7c34919b8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user, amount, gas_fees, timestamp = arbitrum_one_accounts[0], '0.007767825959188763', '0.000001382891214', TimestampMS(1712328694000)  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=user,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user,
            notes=f'Wrap {amount} ETH in WETH',
            counterparty=CPT_WETH,
            address=WETH_ARB_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WETH_ARB,
            amount=FVal(amount),
            location_label=user,
            notes=f'Receive {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_ARB_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x81aa5101D4c376cd6DC031EA62D7b64A9BAE10a0']])
def test_weth_withdraw_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4a6b47e1f622a8ad059bd0723c53f2c71f12e7b105d2ef2ff4dff07ac1f185c0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712240095000)
    amount, gas_fees = '0.000518962654328944', '0.000001897927938075'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH_OPT,
            amount=FVal(amount),
            location_label=optimism_accounts[0],
            notes=f'Unwrap {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {amount} ETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0xD6f30247e6a8B8656a8B02Ea37247f5eb939c626']])
def test_weth_deposit_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x42074e2228be1716f84888f1993fa62443f591945b21dfbf159a64ae467990c4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712241853000)
    amount, gas_fees = '0.0345', '0.000002820767318933'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=optimism_accounts[0],
            notes=f'Wrap {amount} ETH in WETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WETH_OPT,
            amount=FVal(amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0x6247666Ea4C80083035214780978E9EBa4AA6Cf4']])
def test_weth_withdraw_scroll(scroll_inquirer, scroll_accounts):
    tx_hash = deserialize_evm_tx_hash('0x88f49633073a7667f93eb888ec2151c26f449cc10afca565a15f8df68ee20f82')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712239879000)
    amount, gas_fees = '0.00211824', '0.000194659253936861'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH_SCROLL,
            amount=FVal(amount),
            location_label=scroll_accounts[0],
            notes=f'Unwrap {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_SCROLL_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=scroll_accounts[0],
            notes=f'Receive {amount} ETH',
            counterparty=CPT_WETH,
            address=WETH_SCROLL_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('scroll_accounts', [['0xdFd21F8aA81c5787160F9a4B39357F5FE1c743DC']])
def test_weth_deposit_scroll(scroll_inquirer, scroll_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1fa6d87801891fcea66a9be2d4fce1c52569c5ce30579fbe7de37eb05bd247f8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712239897000)
    amount, gas_fees = '0.135', '0.000199290832110225'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(0.135),
            location_label=scroll_accounts[0],
            notes=f'Wrap {amount} ETH in WETH',
            counterparty=CPT_WETH,
            address=WETH_SCROLL_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WETH_SCROLL,
            amount=FVal(0.135),
            location_label=scroll_accounts[0],
            notes=f'Receive {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_SCROLL_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x44f29ebE386c409376C66ad268F9Ae595c8C3e76']])
def test_weth_withdraw_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8d54608c2f684d880ad40a16cf9b82525c51520798ae8875d543d3338327ddad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712239837000)
    amount, gas_fees = '0.00022448658511341', '0.000000533995613184'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH_BASE,
            amount=FVal(amount),
            location_label=base_accounts[0],
            notes=f'Unwrap {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=base_accounts[0],
            notes=f'Receive {amount} ETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0xf396e7dbb20489D47F2daBfDA013163223B892a0']])
def test_weth_deposit_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0d418e4a858ca5faf00c36b685561ca0fdac52ebd10364bf2cb6d7b5969e84e5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712239899000)
    amount, gas_fees = '1.2', '0.000000775794575663'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=base_accounts[0],
            notes=f'Wrap {amount} ETH in WETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WETH_BASE,
            amount=FVal(amount),
            location_label=base_accounts[0],
            notes=f'Receive {amount} WETH',
            counterparty=CPT_WETH,
            address=WETH_OP_BASE_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0x33C0Aae5b2b6Eae2a6286B3a6621B55DcC02dC9e']])
def test_wmatic_deposit_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0xba581391d417a6dcc31031f1cf7cba6e63b701a8680828445ffdde73777843e1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712851902000)
    amount, gas_fees = '119.97566999849747', '0.007112105381183941'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Wrap {amount} POL in WMATIC',
            counterparty=CPT_WMATIC,
            address=WMATIC_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WMATIC,
            amount=FVal(amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {amount} WMATIC',
            counterparty=CPT_WMATIC,
            address=WMATIC_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0xdAA9E3CA7500d7Ba3855dF9d8BCCde229C13919e']])
def test_wmatic_withdraw_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe90ed71875ff44ea45ea960d006ec4c0ccb86506cba494471aba4ba9dc86123f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1712851796000)
    amount, gas_fees = '4.9750995', '0.007687202027240021'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WMATIC,
            amount=FVal(amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Unwrap {amount} WMATIC',
            counterparty=CPT_WMATIC,
            address=WMATIC_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {amount} POL',
            counterparty=CPT_WMATIC,
            address=WMATIC_ADDRESS,
        ),
    ]
    assert events == expected_events
