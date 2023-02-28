import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_CDAI, A_CETH, A_COMP, A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, Timestamp, deserialize_evm_tx_hash

ADDY = '0x5727c0481b90a129554395937612d8b9301D6c7b'
ADDY2 = '0x87Dd56068Af560B0D8472C4EF41CB902FCbF5ebE'
ADDY3 = '0xb99CC7e10Fe0Acc68C50C7829F473d81e23249cc'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_compound_ether_deposit(database, ethereum_inquirer):
    """Data taken from:
    https://etherscan.io/tx/0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39
    """
    tx_hash = deserialize_evm_tx_hash('0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1598639099000,
            location=Location.ETHEREUM,
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
            location=Location.ETHEREUM,
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
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_CETH,
            balance=Balance(amount=FVal('24.97649991'), usd_value=ZERO),
            location_label=ADDY,
            notes='Receive 24.97649991 cETH from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_compound_ether_withdraw(database, ethereum_inquirer):
    """Data taken from:
    https://etherscan.io/tx/0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807
    """
    tx_hash = deserialize_evm_tx_hash('0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1598813490000,
            location=Location.ETHEREUM,
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
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_CETH,
            balance=Balance(amount=FVal('24.97649991'), usd_value=ZERO),
            location_label=ADDY,
            notes='Return 24.97649991 cETH to compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=50,
            timestamp=1598813490000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.500003923413507454'), usd_value=ZERO),
            location_label=ADDY,
            notes='Withdraw 0.500003923413507454 ETH from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY2]])
def test_compound_deposit_with_comp_claim(
        database,
        ethereum_inquirer,
):
    """Data taken from:
    https://etherscan.io/tx/0xfdbfe6e9ce822bd988054945c86f2dff1fac6a12b4acb0b68c8805b5aa3b30ba
    """
    tx_hash = deserialize_evm_tx_hash('0xfdbfe6e9ce822bd988054945c86f2dff1fac6a12b4acb0b68c8805b5aa3b30ba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
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
            location=Location.ETHEREUM,
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
            location=Location.ETHEREUM,
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
            location=Location.ETHEREUM,
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
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_CDAI,
            balance=Balance(amount=wrapped_amount),
            location_label=ADDY2,
            notes=f'Receive {wrapped_amount} cDAI from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY3]])
def test_compound_multiple_comp_claim(database, ethereum_inquirer):
    """Test that a transaction with multiple comp claims decodes all of them as rewards

    This is to test against a regression of a bug that decoded the last reward claim
    as a simple receive.
    """
    tx_hash = deserialize_evm_tx_hash('0x25d341421044fa27006c0ec8df11067d80f69b2d2135065828f1992fa6868a49')  # noqa: E501
    timestamp = Timestamp(1622430975000)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.074799254'), usd_value=ZERO),
            location_label=ADDY3,
            notes='Burned 0.074799254 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=25,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=FVal('3.037897781413961524'), usd_value=ZERO),
            location_label=ADDY3,
            notes='Collect 3.037897781413961524 COMP from compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=FVal('0.03855352439614718'), usd_value=ZERO),
            location_label=ADDY3,
            notes='Collect 0.03855352439614718 COMP from compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=FVal('0.000186677589499495'), usd_value=ZERO),
            location_label=ADDY3,
            notes='Collect 0.000186677589499495 COMP from compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=39,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=FVal('0.001710153220923912'), usd_value=ZERO),
            location_label=ADDY3,
            notes='Collect 0.001710153220923912 COMP from compound',
            counterparty=CPT_COMPOUND,
        ), HistoryBaseEntry(  # this appeared as Receive at time of writing the test
            event_identifier=tx_hash,
            sequence_index=44,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            balance=Balance(amount=FVal('0.000000000000000015'), usd_value=ZERO),
            location_label=ADDY3,
            notes='Collect 0.000000000000000015 COMP from compound',
            counterparty=CPT_COMPOUND,
        )]
    assert events == expected_events
