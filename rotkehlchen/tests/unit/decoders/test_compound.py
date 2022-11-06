import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.constants.assets import A_CDAI, A_CETH, A_COMP, A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x5727c0481b90a129554395937612d8b9301D6c7b'
ADDY2 = '0x87Dd56068Af560B0D8472C4EF41CB902FCbF5ebE'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_compound_ether_deposit(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from:
    https://etherscan.io/tx/0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1598639099000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.014122318'), usd_value=ZERO),
            location_label=ADDY,
            notes='Burned 0.014122318 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=1,
            timestamp=1598639099000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.5'), usd_value=ZERO),
            location_label=ADDY,
            notes='Deposit 0.5 ETH to compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=33,
            timestamp=1598639099000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_CETH,
            balance=Balance(amount=FVal('24.97649991'), usd_value=ZERO),
            location_label=ADDY,
            notes='Receive 24.97649991 cETH from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_compound_ether_withdraw(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from:
    https://etherscan.io/tx/0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1598813490000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.02858544'), usd_value=ZERO),
            location_label=ADDY,
            notes='Burned 0.02858544 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=1,
            timestamp=1598813490000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_CETH,
            balance=Balance(amount=FVal('24.97649991'), usd_value=ZERO),
            location_label=ADDY,
            notes='Return 24.97649991 cETH to compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=2,
            timestamp=1598813490000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.500003923413507454'), usd_value=ZERO),
            location_label=ADDY,
            notes='Withdraw 0.500003923413507454 ETH from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY2]])
def test_compound_deposit_with_comp_claim(
        database,
        ethereum_manager,
        function_scope_messages_aggregator,
):
    """Data taken from:
    https://etherscan.io/tx/0xfdbfe6e9ce822bd988054945c86f2dff1fac6a12b4acb0b68c8805b5aa3b30ba
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0xfdbfe6e9ce822bd988054945c86f2dff1fac6a12b4acb0b68c8805b5aa3b30ba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    amount = FVal('14309.930911242041089052')
    wrapped_amount = FVal('687371.5068874')
    interest = FVal('0.076123031460129653')
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1607572696000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00945248'), usd_value=ZERO),
            location_label=ADDY2,
            notes='Burned 0.00945248 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=241,
            timestamp=1607572696000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=interest),
            location_label=ADDY2,
            notes=f'Collect {interest} COMP from compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=243,
            timestamp=1607572696000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=amount),
            location_label=ADDY2,
            notes=f'Deposit {amount} DAI to compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=250,
            timestamp=1607572696000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_CDAI,
            balance=Balance(amount=wrapped_amount),
            location_label=ADDY2,
            notes=f'Receive {wrapped_amount} cDAI from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events
