from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.compound.constants import (
    COMPTROLLER_PROXY_ADDRESS,
    CPT_COMPOUND,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_CBAT,
    A_CDAI,
    A_CETH,
    A_COMP,
    A_CUSDC,
    A_DAI,
    A_ETH,
    A_USDC,
    A_USDT,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

ADDY = '0x5727c0481b90a129554395937612d8b9301D6c7b'
ADDY2 = '0x87Dd56068Af560B0D8472C4EF41CB902FCbF5ebE'
ADDY3 = '0xb99CC7e10Fe0Acc68C50C7829F473d81e23249cc'
ADDR_BORROWS = '0xD84101AE36b83E64b52AC9a61Efa4497f8FD2560'
ADDR_BORROWS_ETH = '0x8492aBE1c9918d5df6c4Fe39Afa9803e52E4698b'
ADDR_REPAYS = '0x9760Bf25166F764f616fF067332c2bDDbf54Dadd'
ADDR_REPAYS_ETH = '0x18c42014Fb0aeD3E35515eb45DF8498Af67773a4'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_compound_ether_deposit(ethereum_inquirer):
    """Data taken from:
    https://etherscan.io/tx/0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39
    """
    tx_hash = deserialize_evm_tx_hash('0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1598639099000)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.014122318'),
            location_label=ADDY,
            notes='Burn 0.014122318 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal('0.5'),
            location_label=ADDY,
            notes='Deposit 0.5 ETH to compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_CETH,
            amount=FVal('24.97649991'),
            location_label=ADDY,
            notes='Receive 24.97649991 cETH from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_compound_ether_withdraw(ethereum_inquirer):
    """Data taken from:
    https://etherscan.io/tx/0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807
    """
    tx_hash = deserialize_evm_tx_hash('0x024bd402420c3ba2f95b875f55ce2a762338d2a14dac4887b78174254c9ab807')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1598813490000)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.02858544'),
            location_label=ADDY,
            notes='Burn 0.02858544 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_CETH,
            amount=FVal('24.97649991'),
            location_label=ADDY,
            notes='Return 24.97649991 cETH to compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal('0.500003923413507454'),
            location_label=ADDY,
            notes='Withdraw 0.500003923413507454 ETH from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
        )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY2]])
def test_compound_deposit_with_comp_claim(ethereum_inquirer):
    """Data taken from:
    https://etherscan.io/tx/0xfdbfe6e9ce822bd988054945c86f2dff1fac6a12b4acb0b68c8805b5aa3b30ba
    """
    tx_hash = deserialize_evm_tx_hash('0xfdbfe6e9ce822bd988054945c86f2dff1fac6a12b4acb0b68c8805b5aa3b30ba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1607572696000)
    amount = FVal('14309.930911242041089052')
    wrapped_amount = FVal('687371.5068874')
    interest = FVal('0.076123031460129653')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00945248'),
            location_label=ADDY2,
            notes='Burn 0.00945248 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=241,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=interest,
            location_label=ADDY2,
            notes=f'Collect {interest} COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=242,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=amount,
            location_label=ADDY2,
            notes=f'Deposit {amount} DAI to compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=243,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_CDAI,
            amount=wrapped_amount,
            location_label=ADDY2,
            notes=f'Receive {wrapped_amount} cDAI from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643'),
        )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY3]])
def test_compound_multiple_comp_claim(ethereum_inquirer):
    """Test that a transaction with multiple comp claims decodes all of them as rewards
    This is to test against a regression of a bug that decoded the last reward claim
    as a simple receive.
    """
    tx_hash = deserialize_evm_tx_hash('0x25d341421044fa27006c0ec8df11067d80f69b2d2135065828f1992fa6868a49')  # noqa: E501
    timestamp = TimestampMS(1622430975000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.074799254'),
            location_label=ADDY3,
            notes='Burn 0.074799254 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=25,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=FVal('3.037897781413961524'),
            location_label=ADDY3,
            notes='Collect 3.037897781413961524 COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=FVal('0.03855352439614718'),
            location_label=ADDY3,
            notes='Collect 0.03855352439614718 COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=FVal('0.000186677589499495'),
            location_label=ADDY3,
            notes='Collect 0.000186677589499495 COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=39,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=FVal('0.001710153220923912'),
            location_label=ADDY3,
            notes='Collect 0.001710153220923912 COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        ), EvmEvent(  # this appeared as Receive at time of writing the test
            tx_ref=tx_hash,
            sequence_index=44,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=FVal('0.000000000000000015'),
            location_label=ADDY3,
            notes='Collect 0.000000000000000015 COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        )]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xB8cCf257d32b134ffecb902e5Bef3042841B8A4A']])
def test_compound_comp_claim_last_transfer(ethereum_inquirer, ethereum_accounts):
    """
    Test comp claim case that was not decoded properly before due to
    the transfer being last the last event
    """
    tx_hash = deserialize_evm_tx_hash('0xbd2dcb1121bf230a855788a77aa054dc1aae7a898cb4a7d7c45c5866f3f887ac')  # noqa: E501
    timestamp = TimestampMS(1622430975000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, amount = TimestampMS(1672433507000), '0.0041468661739364', '12.817402848098541218'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=61,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_COMP,
        amount=FVal(amount),
        location_label=ethereum_accounts[0],
        notes=f'Collect {amount} COMP from compound',
        counterparty=CPT_COMPOUND,
        address=COMPTROLLER_PROXY_ADDRESS,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDR_BORROWS]])
def test_compound_borrow(ethereum_inquirer: 'EthereumInquirer') -> None:
    """Data taken from:
    https://etherscan.io/tx/0x036338316a076590a496791a729d3459934a89d6eb512f765cf0e28f9eb8b50c
    """
    tx_hash = deserialize_evm_tx_hash('0x036338316a076590a496791a729d3459934a89d6eb512f765cf0e28f9eb8b50c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1578114925000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002977007'),
            location_label=ADDR_BORROWS,
            notes='Burn 0.002977007 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=9,
            timestamp=TimestampMS(1578114925000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_USDC,
            amount=FVal(1500000),
            location_label=ADDR_BORROWS,
            notes='Borrow 1500000 USDC from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x39AA39c021dfbaE8faC545936693aC917d5E7563'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDR_REPAYS]])
def test_compound_payback(ethereum_inquirer: 'EthereumInquirer') -> None:
    """Data taken from:
    https://etherscan.io/tx/0x000da925508a1a2f322f6fb74592baf9a75bb9f971cb3a72a5deb0526d39757d
    """
    tx_hash = deserialize_evm_tx_hash('0x000da925508a1a2f322f6fb74592baf9a75bb9f971cb3a72a5deb0526d39757d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1605818798000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0037086'),
            location_label=ADDR_REPAYS,
            notes='Burn 0.0037086 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=246,
            timestamp=TimestampMS(1605818798000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_COMP,
            amount=FVal('1.209128558800877907'),
            location_label=ADDR_REPAYS,
            notes='Collect 1.209128558800877907 COMP from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=248,
            timestamp=TimestampMS(1605818798000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDC,
            amount=FVal(11637.762191),
            location_label=ADDR_REPAYS,
            notes='Repay 11637.762191 USDC to compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x39AA39c021dfbaE8faC545936693aC917d5E7563'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDR_BORROWS_ETH]])
def test_compound_borrow_eth(ethereum_inquirer: 'EthereumInquirer') -> None:
    """Data taken from:
    https://etherscan.io/tx/0x00035065f364453ca4585ab5d4ee7dacc59a3f7acc305644c334fdfff3a2527f
    """
    tx_hash = deserialize_evm_tx_hash('0x00035065f364453ca4585ab5d4ee7dacc59a3f7acc305644c334fdfff3a2527f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1581618106000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001882176'),
            location_label=ADDR_BORROWS_ETH,
            notes='Burn 0.001882176 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1581618106000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_ETH,
            amount=FVal(0.1),
            location_label=ADDR_BORROWS_ETH,
            notes='Borrow 0.1 ETH from compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDR_REPAYS_ETH]])
def test_compound_repays_eth(ethereum_inquirer: 'EthereumInquirer') -> None:
    """Data taken from:
    https://etherscan.io/tx/0x0007416c8caa441ce07c61dbf2455b3068d21d9bffbfbbfca9f1016d7c3ca33f
    """
    tx_hash = deserialize_evm_tx_hash('0x0007416c8caa441ce07c61dbf2455b3068d21d9bffbfbbfca9f1016d7c3ca33f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1590532744000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003931524'),
            location_label=ADDR_REPAYS_ETH,
            notes='Burn 0.003931524 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1590532744000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_ETH,
            amount=FVal(0.2),
            location_label=ADDR_REPAYS_ETH,
            notes='Repay 0.2 ETH to compound',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0xf859A1AD94BcF445A406B892eF0d3082f4174088'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9bf62c518ffe86bD43D57c7026aA1A4fBeA83b15']])
def test_compound_liquidate(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts,
) -> None:
    """
    Decode a liquidation happening to the position of 0x9bf62c518ffe86bD43D57c7026aA1A4fBeA83b15
    """
    tx_hash = deserialize_evm_tx_hash('0x0001a89e439c3673b8264f880730784ebd698502bb9dd62949d42a66a4129f23')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=267,
            timestamp=TimestampMS(1652292368000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.LOSS,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=A_CBAT,
            amount=FVal(258831.42924011),
            location_label=ethereum_accounts[0],
            notes='Lost 258831.42924011 cBAT in a compound forced liquidation to repay 1907.307144 USDT',  # noqa: E501
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0xD911560979B78821D7b045C79E36E9CbfC2F6C6F'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD911560979B78821D7b045C79E36E9CbfC2F6C6F']])
def test_compound_liquidator_side(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts,
) -> None:
    """
    Decode liquidation made by 0xD911560979B78821D7b045C79E36E9CbfC2F6C6F
    """
    tx_hash = deserialize_evm_tx_hash('0x0001a89e439c3673b8264f880730784ebd698502bb9dd62949d42a66a4129f23')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=263,
            timestamp=TimestampMS(1652292368000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDT,
            amount=FVal(1907.307144),
            location_label=ethereum_accounts[0],
            notes='Repay 1907.307144 USDT in a compound liquidation',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0xf650C3d88D12dB855b8bf7D11Be6C55A4e07dCC9'),
            extra_data={'in_liquidation': True},
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=267,
            timestamp=TimestampMS(1652292368000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=A_CBAT,
            amount=FVal(258831.42924011),
            location_label=ethereum_accounts[0],
            notes='Collect 258831.42924011 cBAT for performing a compound liquidation',
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x9bf62c518ffe86bD43D57c7026aA1A4fBeA83b15'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC440f3C87DC4B6843CABc413916220D4f4FeD117']])
def test_compound_liquidation_eth(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts,
) -> None:
    """Test that repaying a compound loan in a liquidation using ETH is correctly decoded"""
    tx_hash = deserialize_evm_tx_hash('0x160c0e6db0df5ea0c1cc9b1b31bd90c842ef793c9b2ab496efdc62bdd80eeb52')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=34,
            timestamp=TimestampMS(1586159213000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.LOSS,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=A_CUSDC,
            amount=FVal(13.06078395),
            location_label=ethereum_accounts[0],
            notes='Lost 13.06078395 cUSDC in a compound forced liquidation to repay 0.00168867571834735 ETH',  # noqa: E501
            counterparty=CPT_COMPOUND,
            address=string_to_evm_address('0x89c745c97495644A44D19654C8AdCaAaCB7Ec263'),
        ),
    ]
