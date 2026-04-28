from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.morpho_blue.constants import CPT_MORPHO_BLUE, MORPHO_BLUE
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.types import (
    string_to_evm_address,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.decoders.test_zerox import A_BASE_USDC
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xB3e305B63bE2cD9EB42d6007a5bB1fE4a13da1e2']])
def test_morpho_blue_supply(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x20d40794ca9f5a14b7ae5ccb032294449f02a94470af7ba24926537785dde07c')  # noqa: E501
    with patch(  # skip internal transactions since this tx does not have any
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    spender = string_to_evm_address('0xE0Eefe4AA0cB32740aDFD8083AbeC255AaC3b379')
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=110,
            timestamp=(timestamp := TimestampMS(1776987637000)),
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_BASE_USDC,
            amount=FVal(deposit_amount := '800'),
            location_label=user_address,
            notes=f'Set USDC spending approval of {user_address} by {spender} to {deposit_amount}',
            address=spender,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=112,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_BASE_USDC,
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC into Morpho Blue',
            counterparty=CPT_MORPHO_BLUE,
            address=MORPHO_BLUE,
            extra_data={'market_id': '0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'},  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=125,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:8453/erc20:0xA10410C6a1aC3C43A231D2871b9A21a2143bfAde'),
            amount=FVal('16000'),
            location_label=user_address,
            notes=f'Receive 16000 ZRL from 0x0000000000000000000000000000000000000000 to {user_address}',  # noqa: E501
            address=string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xe17C7f14FB0b2F41fbfdCe69346Ba5C192705c91']])
def test_morpho_blue_borrow(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xcfffd4c6c60dfa3a94466959e365ff57124ccdc1e31f97b75238b757658d3121')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1716314189000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000016064193613886'),
        location_label=user_address,
        notes='Burn 0.000016064193613886 ETH for gas',
        counterparty='gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=41,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_BASE_USDC,
        amount=FVal('7'),
        location_label=user_address,
        notes='Borrow 7 USDC from Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0xdba352d93a64b17c71104cbddc6aef85cd432322a1446b5b65163cbbc615cd0c'},  # noqa: E501
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x20e74013d82fea853AfCa3b4CB1Fd9C2B105F55a']])
def test_morpho_blue_repay(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb40d2edb688afbca34c2dc9cbd364ce83a66e0a55f421231ac4d88281009866f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert EvmEvent(
        tx_ref=tx_hash,
        sequence_index=241,
        timestamp=TimestampMS(1718704585000),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.PAYBACK_DEBT,
        asset=A_BASE_USDC,
        amount=FVal('0.500002'),
        location_label=base_accounts[0],
        notes='Repay 0.500002 USDC to Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0xdba352d93a64b17c71104cbddc6aef85cd432322a1446b5b65163cbbc615cd0c'},  # noqa: E501
    ) in events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x2E97fcA0F192AA0f73D7915c7c9a67Fc8991d1A6']])
def test_morpho_blue_withdrawal(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc261393f91a1a295bf06f154db64b43de40c9bc2d6310f84a3d2c2a25f590975')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=283,
        timestamp=(timestamp := TimestampMS(1718111885000)),
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        asset=A_BASE_USDC,
        amount=ONE,
        location_label=(user_address := base_accounts[0]),
        notes='Withdraw 1 USDC from Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'},  # noqa: E501
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=284,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label='0xD2a43D48B92EcFcf971bA0401B7243429b7A78C8',
        notes=f'Successfully executed safe transaction 0xaea91b4e8e31ef0570f725e0121b86c7296a8461aa788267556b9013fd6c98db for multisig {user_address}',  # noqa: E501
        counterparty=CPT_SAFE_MULTISIG,
        address=user_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x20e74013d82fea853AfCa3b4CB1Fd9C2B105F55a']])
def test_morpho_blue_withdraw_collateral(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x6f22fe65f25aa9e68e4fc8b43d742da52318259531c02c7369342e19a67a0227')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert EvmEvent(
        tx_ref=tx_hash,
        sequence_index=165,
        timestamp=TimestampMS(1718711139000),
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        asset=Asset('eip155:8453/erc20:0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22'),
        amount=FVal('0.001'),
        location_label=base_accounts[0],
        notes='Withdraw 0.001 cbETH collateral from Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0xdba352d93a64b17c71104cbddc6aef85cd432322a1446b5b65163cbbc615cd0c'},  # noqa: E501
    ) in events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xf9c9EDb4A1D096d3580dcB4F8E4a7F7211faB2Bb']])
def test_morpho_blue_supply_collateral(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xe0500c132dd33e402613a8f8d933f396d6002f10b51b41d0b20b91ead27ef032')  # noqa: E501
    with patch(  # skip internal transactions since this tx does not have any
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert EvmEvent(
        tx_ref=tx_hash,
        sequence_index=452,
        timestamp=TimestampMS(1777045159000),
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
        asset=Asset('eip155:8453/erc20:0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'),
        amount=FVal('0.00003582'),
        location_label=base_accounts[0],
        notes='Deposit 0.00003582 cbBTC as collateral into Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836'},  # noqa: E501
    ) in events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x4Dfb028A4d1353D0f0fb876cd9F4eD643E04Cf27']])
def test_morpho_blue_supply_via_bundler(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a supply event through the Morpho bundler.

    In this transaction the user supplies USDC to Morpho Blue via the bundler.
    The Supply event's caller is the bundler while onBehalf is the user.
    The user's USDC transfer goes to the bundler first, then the bundler
    forwards it to Morpho. The decoder should match the user's spend event
    to the Supply log and transform it into a deposit.
    """
    tx_hash = deserialize_evm_tx_hash('0xe01c02cfb316b1520a55c3cfb43b357bf61120f45a6374a1af4510e3beea678d')  # noqa: E501
    with patch(
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    assert EvmEvent(
        tx_ref=tx_hash,
        sequence_index=485,
        timestamp=TimestampMS(1777287081000),
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
        asset=A_BASE_USDC,
        amount=FVal('0.5'),
        location_label=user_address,
        notes='Deposit 0.5 USDC into Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'},  # noqa: E501
    ) in events
    assert not any(
        e.event_type == HistoryEventType.SPEND and e.event_subtype == HistoryEventSubType.NONE and e.asset == A_BASE_USDC  # noqa: E501
        for e in events
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x4Dfb028A4d1353D0f0fb876cd9F4eD643E04Cf27']])
def test_morpho_blue_supply_collateral_and_borrow_via_bundler(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a supply collateral + borrow through the Morpho bundler.

    The Morpho bundler performs operations on behalf of the user, so the caller
    in the Morpho events is the bundler contract while the onBehalf is the user.
    This test ensures that the supply collateral is correctly matched to the user.
    """
    tx_hash = deserialize_evm_tx_hash('0x90a83a26d46fbdb0a85f5cbaa5f7cb7df21795d664ffe5b247c7076ae51bbcf2')  # noqa: E501
    with patch(
        'rotkehlchen.chain.evm.transactions.'
        'EvmTransactions._query_and_save_internal_transactions_for_parent_hash',
        return_value=[],
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    assert EvmEvent(
        tx_ref=tx_hash,
        sequence_index=315,
        timestamp=(timestamp := TimestampMS(1777287621000)),
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
        asset=Asset('eip155:8453/erc20:0x4200000000000000000000000000000000000006'),
        amount=FVal('0.0002'),
        location_label=user_address,
        notes='Deposit 0.0002 WETH as collateral into Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'},  # noqa: E501
    ) in events
    assert EvmEvent(
        tx_ref=tx_hash,
        sequence_index=321,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_BASE_USDC,
        amount=FVal('0.1'),
        location_label=user_address,
        notes='Borrow 0.1 USDC from Morpho Blue',
        counterparty=CPT_MORPHO_BLUE,
        address=MORPHO_BLUE,
        extra_data={'market_id': '0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'},  # noqa: E501
    ) in events
