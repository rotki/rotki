from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3630220f243288E3EAC4C5676fC191CFf5756431']])
def test_gearbox_deposit(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x04e3bcebf71873a5de1c4d9b40f1c97631a3958ef0d8d743a1a1b4d50361855d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1716770963000), '0.0006562535', '156164.834098036387706577', '151038.694912640397702932'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=513,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} DAI to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x1aD0780a152fE66FAf7c44A7F875A36b1bf790F0'),
        ), EvmEvent(
            sequence_index=520,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC853E4DA38d9Bd1d01675355b8c8f3BBC1451973'),
            balance=Balance(amount=FVal(lp_token_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Receive {lp_token_amount} farmdDAIV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x1aD0780a152fE66FAf7c44A7F875A36b1bf790F0'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb99a2c4C1C4F1fc27150681B740396F6CE1cBcF5']])
def test_gearbox_deposit_usdc(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x92d178bbe5152cad47029b0c130450848ee46084e72addd09ba955631af1325b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1716899027000), '0.004946659515956316', '6500000', '6147276.510091'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=154,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_USDC,
            balance=Balance(amount=FVal(6500000)),
            location_label=ethereum_accounts[0],
            notes=f'Set USDC spending approval of {ethereum_accounts[0]} by 0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25 to {deposit_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25'),
        ), EvmEvent(
            sequence_index=155,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_USDC,
            balance=Balance(amount=FVal(deposit_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} USDC to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25'),
        ), EvmEvent(
            sequence_index=162,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x9ef444a6d7F4A5adcd68FD5329aA5240C90E14d2'),
            balance=Balance(amount=FVal(lp_token_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Receive {lp_token_amount} farmdUSDCV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9167B9d55BA7E7D6163bAAa97C099dfE3d1D9420']])
def test_gearbox_withdraw(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xb286e618ec2e5961c696df1855006dea0343fb635c7f199621f8592db342dfba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas, lp_amount, withdrawn = TimestampMS(1716739091000), '0.002506078391975991', '29394.203983328624199078', '30388.281725016794033508'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=500,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC853E4DA38d9Bd1d01675355b8c8f3BBC1451973'),
            balance=Balance(amount=FVal(lp_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Return {lp_amount} farmdDAIV3',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x1aD0780a152fE66FAf7c44A7F875A36b1bf790F0'),
        ), EvmEvent(
            sequence_index=504,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal(withdrawn)),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {withdrawn} DAI from Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xe7146F53dBcae9D6Fa3555FE502648deb0B2F823'),
        ),
    ]
    assert events == expected_events
