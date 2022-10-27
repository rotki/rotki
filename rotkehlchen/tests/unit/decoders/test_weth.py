import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.weth.constants import CPT_WETH
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, EvmTokenKind, Location, deserialize_evm_tx_hash
from rotkehlchen.user_messages import MessagesAggregator


@pytest.mark.parametrize('ethereum_accounts', [['0x4B078a6A7026C32D2D6Aff763E2F37336cf552Dd']])  # noqa: E501
def test_weth_deposit(database, ethereum_manager):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=msg_aggregator,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf',
            ),
            sequence_index=0,
            timestamp=1666256147000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf',
            ),
            sequence_index=1,
            timestamp=1666256147000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x5bb623b365def9650816dcbaf1babde8fd0ebed737db36d3a033d7cf63792daf',
            ),
            sequence_index=2,
            timestamp=1666256147000,
            location=Location.BLOCKCHAIN,
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
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3']])  # noqa: E501
def test_weth_withdrawal(database, ethereum_manager):
    """
    Data for withdrawal is taken from
    https://etherscan.io/tx/0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=msg_aggregator,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07',
            ),
            sequence_index=0,
            timestamp=1666256147000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07',
            ),
            sequence_index=1,
            timestamp=1666256147000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WETH,
            balance=Balance(amount=FVal(0.5)),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Unwrap 0.5 WETH',
            counterparty=CPT_WETH,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x1f3aa6f7d33bfaaaf9cdd92b16fecdf911341601c02ad89b4ec0b80c66c28a07',
            ),
            sequence_index=2,
            timestamp=1666256147000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.5)),
            location_label='0x4b2975AfF4DeF34D3Cd4f4759b45faF738D790D3',
            notes='Receive 0.5 ETH',
            counterparty=CPT_WETH,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xC4DdFf531132d32b47eC938AcfA28E354769A806']])  # noqa: E501
def test_weth_interaction_with_protocols_deposit(database, ethereum_manager):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=msg_aggregator,
        tx_hash=evmhash,
    )
    assert len(events) == 4
    tx_hash = HistoryBaseEntry.deserialize_event_identifier(
        '0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9',
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1666595591000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.004777703202235758')),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Burned 0.004777703202235758 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0xab0dec3785632c567365c48ea1fd1178f0998773136a555912625d2668ef53e9',
            ),
            sequence_index=1,
            timestamp=1666595591000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.999999999949533767')),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Send 0.999999999949533767 ETH to 0xC36442b4a4522E871399CD717aBDD847Ab11FE88',  # noqa: E501
            counterparty='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=187,
            timestamp=1666595591000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC,
            balance=Balance(amount=FVal('294.145955')),
            location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
            notes='Send 294.145955 USDC from 0xC4DdFf531132d32b47eC938AcfA28E354769A806 to 0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8',  # noqa: E501
            counterparty='0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8',
        ),
    ]
    assert events[:-1] == expected_events
    expected_erc721 = get_or_create_evm_token(
        userdb=database,
        evm_address='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        ethereum_manager=ethereum_manager,
    )
    assert events[3] == HistoryBaseEntry(
        event_identifier=tx_hash,
        sequence_index=191,
        timestamp=1666595591000,
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=expected_erc721,
        balance=Balance(amount=ONE),
        location_label='0xC4DdFf531132d32b47eC938AcfA28E354769A806',
        notes='Receive Uniswap V3 Positions NFT-V1 with id 343053 from 0x0000000000000000000000000000000000000000 to 0xC4DdFf531132d32b47eC938AcfA28E354769A806',  # noqa: E501
        counterparty='0x0000000000000000000000000000000000000000',
        extra_data={'token_id': 343053, 'token_name': 'Uniswap V3 Positions NFT-V1'},
    )


@pytest.mark.parametrize('ethereum_accounts', [['0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47']])  # noqa: E501
def test_weth_interaction_with_protocols_withdrawal(database, ethereum_manager):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=msg_aggregator,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167',
            ),
            sequence_index=0,
            timestamp=1666284551000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.011940359686863452')),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Burned 0.011940359686863452 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167',
            ),
            sequence_index=1,
            timestamp=1666284551000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.764522981784947382')),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Receive 0.764522981784947382 ETH from 0xC36442b4a4522E871399CD717aBDD847Ab11FE88',  # noqa: E501
            counterparty='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        ), HistoryBaseEntry(
            event_identifier=HistoryBaseEntry.deserialize_event_identifier(
                '0x4a811e8cfa58cb5bd57d92d62e1f01c8578859705243fe69c6bd9e59f3dcd167',
            ),
            sequence_index=243,
            timestamp=1666284551000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC,
            balance=Balance(amount=FVal('1028.82092')),
            location_label='0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',
            notes='Receive 1028.82092 USDC from 0xC36442b4a4522E871399CD717aBDD847Ab11FE88 to 0xDea6866A866C60d68fFDFc6178C12fCFdb9d0D47',  # noqa: E501
            counterparty='0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d']])  # noqa: E501
def test_weth_interaction_errors(database, ethereum_manager):
    # check that if no out event occurs, an in event should not be created for deposit event
    # https://etherscan.io/tx/0x4ca19c97b7533e74f36dff18acf0115055f63f9d8ae078dfc8ab15ceb14d2f2d
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x4ca19c97b7533e74f36dff18acf0115055f63f9d8ae078dfc8ab15ceb14d2f2d'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=msg_aggregator,
        tx_hash=evmhash,
    )
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1666800983000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.003535483550478045)),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Burned 0.003535483550478045 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1666800983000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.06693824468797216)),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Send 0.06693824468797216 ETH to 0xe66B31678d6C16E9ebf358268a790B763C133750',
            counterparty='0xe66B31678d6C16E9ebf358268a790B763C133750',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            timestamp=1666800983000,
            sequence_index=181,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_USDC,
            balance=Balance(amount=FVal(103.562282)),
            location_label='0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',
            notes='Receive 103.562282 USDC from 0xe66B31678d6C16E9ebf358268a790B763C133750 to 0xF5f5C8924db9aa5E70Bdf7842473Ee8C7F1F4c9d',  # noqa: E501,
            counterparty='0xe66B31678d6C16E9ebf358268a790B763C133750',
        ),
    ]
    assert events == expected_events
