import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.uniswap.constants import CPT_UNISWAP_V3
from rotkehlchen.chain.ethereum.modules.weth.constants import CPT_WETH
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, EvmTokenKind, Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd']])
def test_weth_deposit(database, ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf
    """
    tx_hex = '0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf'
    timestamp = TimestampMS(1666256147000)
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal('0.00057313513694104'),
                usd_value=ZERO,
            ),
            location_label='0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd',
            notes='Burned 0.00057313513694104 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.06),
                usd_value=ZERO,
            ),
            location_label='0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd',
            notes='Wrap 0.06 ETH in WETH',
            counterparty=CPT_WETH,
            address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WETH,
            balance=Balance(
                amount=FVal(0.06),
                usd_value=ZERO,
            ),
            location_label='0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd',
            notes='Receive 0.06 WETH',
            counterparty=CPT_WETH,
            address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3']])
def test_weth_withdrawal(database, ethereum_inquirer):
    """
    Data for withdrawal is taken from
    https://etherscan.io/tx/0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07
    """
    tx_hex = '0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    timestamp = TimestampMS(1666256147000)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal('0.00062372398538032'),
                usd_value=ZERO,
            ),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Burned 0.00062372398538032 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH,
            balance=Balance(amount=FVal(0.5)),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Unwrap 0.5 WETH',
            counterparty=CPT_WETH,
            address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.5)),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Receive 0.5 ETH',
            counterparty=CPT_WETH,
            address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xC4DdFf531132d32b47eC938AcfA28E354769A806']])
def test_weth_interaction_with_protocols_deposit(database, ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9
    """
    tx_hex = '0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9'
    timestamp = TimestampMS(1666595591000)
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 4
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.004777703202235758')),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Burned 0.004777703202235758 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.999999999949533767')),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Deposit 0.999999999949533767 ETH to uniswap-v3 LP 343053',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=187,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('294.145955')),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Deposit 294.145955 USDC to uniswap-v3 LP 343053',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8'),
        ),
    ]
    assert events[:-1] == expected_events
    expected_erc721 = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        evm_inquirer=ethereum_inquirer,
    )
    assert events[3] == EvmEvent(
        tx_hash=evmhash,
        sequence_index=191,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPLOY,
        event_subtype=HistoryEventSubType.NFT,
        asset=expected_erc721,
        balance=Balance(amount=ONE),
        location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
        notes='Create uniswap-v3 LP with id 343053',
        counterparty=CPT_UNISWAP_V3,
        address=ZERO_ADDRESS,
        extra_data={'token_id': 343053, 'token_name': 'Uniswap V3 Positions NFT-V1'},
    )


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47']])
def test_weth_interaction_with_protocols_withdrawal(database, ethereum_inquirer):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167
    """
    tx_hex = '0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167'
    timesatmp = TimestampMS(1666284551000)
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timesatmp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.011940359686863452')),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Burned 0.011940359686863452 ETH for gas',
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
            balance=Balance(amount=FVal('0.764522981784947382')),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Remove 0.764522981784947382 ETH from uniswap-v3 LP 337559',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=243,
            timestamp=timesatmp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal('1028.82092')),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Remove 1028.82092 USDC from uniswap-v3 LP 337559',
            counterparty=CPT_UNISWAP_V3,
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d']])
def test_weth_interaction_errors(database, ethereum_inquirer):
    """
    Check that if no out event occurs, an in event should not be created for deposit event
    https://etherscan.io/tx/0x4ca19c97b7533e74f36dff18acf0115055f63f9d8ae078dfc8ab15ceb14d2f2d
    """
    tx_hex = '0x4ca19c97b7533e74f36dff18acf0115055f63f9d8ae078dfc8ab15ceb14d2f2d'
    timestamp = TimestampMS(1666800983000)
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.003535483550478045)),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Burned 0.003535483550478045 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.06693824468797216)),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Send 0.06693824468797216 ETH to 0xe66B31678d6C16E9ebf358268a790B763C133750',
            address=string_to_evm_address('0xe66B31678d6C16E9ebf358268a790B763C133750'),
        ), EvmEvent(
            tx_hash=evmhash,
            timestamp=timestamp,
            sequence_index=181,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC,
            balance=Balance(amount=FVal(103.562282)),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Receive 103.562282 USDC from 0xe66B31678d6C16E9ebf358268a790B763C133750 to 0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',  # noqa: E501
            address=string_to_evm_address('0xe66B31678d6C16E9ebf358268a790B763C133750'),
        ),
    ]
    assert events == expected_events
