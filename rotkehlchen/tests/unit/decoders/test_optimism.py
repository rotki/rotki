from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.chain.optimism.modules.airdrops.decoder import (
    OPTIMISM_AIRDROP_1,
    OPTIMISM_AIRDROP_4,
)
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.constants.assets import A_ETH, A_OP
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.utils import set_token_spam_protocol
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    SPAM_PROTOCOL,
    ChainID,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_optimism_airdrop_1_claim(optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0xda810d7e1757c6ce7387b437c26472f802eec47404e60d4f1eaa9f23bf8d8b73
    """
    tx_hash = deserialize_evm_tx_hash('0xda810d7e1757c6ce7387b437c26472f802eec47404e60d4f1eaa9f23bf8d8b73')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1673337921000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0002038856162166')),
            location_label=ADDY,
            notes='Burned 0.0002038856162166 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_OP,
            balance=Balance(amount=FVal('827.759804739626467328')),
            location_label=ADDY,
            notes='Claim 827.759804739626467328 OP from the optimism airdrop 1',
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_AIRDROP_1,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'optimism_1'},
        )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x168FEB2E7de2aC0c37a239261D3F9e1b396F22a2']])
def test_optimism_airdrop_4_claim(optimism_accounts, optimism_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xb5b478b321a81ae03565dd72bd625fcb203a97f017670b28e306a893414ae83b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, claim_amount = TimestampMS(1712777987000), '0.000007620095114963', '6000'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=optimism_accounts[0],
            notes=f'Burned {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=80,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_OP,
            balance=Balance(amount=FVal(claim_amount)),
            location_label=optimism_accounts[0],
            notes=f'Claim {claim_amount} OP from the optimism airdrop 4',
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_AIRDROP_4,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'optimism_4'},
        )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_optimism_delegate_change(optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0xe0b31814f787385ab9f680c2ecf7e20e6dd2f880d979a44487768add26faa594
    """
    tx_hash = deserialize_evm_tx_hash('0xe0b31814f787385ab9f680c2ecf7e20e6dd2f880d979a44487768add26faa594')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1673338011000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00005701303160652')),
            location_label=ADDY,
            notes='Burned 0.00005701303160652 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=ADDY,
            notes=f'Change OP Delegate from {ADDY} to {ADDY}',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x4200000000000000000000000000000000000042'),
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x14Acfa256475680e74C8f4c6D7dE32E51DfC3D1a']])
def test_spam_detection(optimism_inquirer: OptimismInquirer):
    get_or_create_evm_token(
        userdb=optimism_inquirer.database,
        evm_address=string_to_evm_address('0x3A5871ef02ba290ABD3fb75684c1C40E06bE5C43'),
        chain_id=ChainID.OPTIMISM,
        fallback_name='Spam token OP',
        fallback_symbol='SPAM OP',
        decimals=18,
        protocol=SPAM_PROTOCOL,
    )
    tx_hash = deserialize_evm_tx_hash('0x4070092c79530835efe9a75eaf1e289da0f38bbb17cd224390bca0a756b7cea4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert len(events) == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x31987a48567Df2E1953A6fb713Faee9fb06d095C']])
def test_spam_detection_exception(
        optimism_inquirer: OptimismInquirer,
        globaldb: 'GlobalDBHandler',
):
    """Example of transaction with a lot of events but mixes transfers and approval events"""
    op_token = A_OP.resolve_to_evm_token()
    with globaldb.conn.write_ctx() as write_cursor:
        set_token_spam_protocol(
            write_cursor=write_cursor,
            token=op_token,
            is_spam=True,
        )

    tx_hash = deserialize_evm_tx_hash('0xe42e27ca8b7084d8970a2e5694ea3d38e9e6570b2f227b177295000ad74c7516')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events[0].event_type == HistoryEventType.RECEIVE
