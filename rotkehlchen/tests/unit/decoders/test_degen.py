from typing import Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
from rotkehlchen.chain.base.modules.degen.constants import (
    CLAIM_AIRDROP_1_CONTRACT,
    CLAIM_AIRDROP_2_CONTRACT,
    CLAIM_AIRDROP_3_CONTRACT,
    CPT_DEGEN,
    DEGEN_TOKEN_ID,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    SupportedBlockchain,
    TimestampMS,
    deserialize_evm_tx_hash,
)

DEGEN_TOKEN: Final = Asset(DEGEN_TOKEN_ID)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_claim_airdrop_2(
        base_accounts: list[ChecksumEvmAddress],
        base_transaction_decoder: BaseTransactionDecoder,
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x885722ab252530e687212799080d5d158d767536b62e0d45a700091a5424bcaa ')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1709555247000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000443147649294366'),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=DEGEN_TOKEN,
            amount=FVal(claimed_amount := '100'),
            location_label=user_address,
            counterparty=CPT_DEGEN,
            address=CLAIM_AIRDROP_2_CONTRACT,
            notes=f'Claim {claimed_amount} DEGEN from Degen airdrop 2',
            extra_data={AIRDROP_IDENTIFIER_KEY: 'degen2_season1'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_claim_airdrop_1(
        base_accounts: list[ChecksumEvmAddress],
        base_inquirer,
        allow_base_routescan: None,
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xba1e5528007c47930d863b63babd9419653dc3275a4b42b94a289ac4fb03cc45')),  # noqa: E501
    )
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1711819697000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000057057590244414')),
        location_label=(user_address := base_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=150,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=DEGEN_TOKEN,
        amount=(claimed_amount := FVal('45995.999999999996854272')),
        location_label=user_address,
        counterparty=CPT_DEGEN,
        address=CLAIM_AIRDROP_1_CONTRACT,
        notes=f'Claim {claimed_amount} DEGEN from Degen airdrop 1',
        extra_data={AIRDROP_IDENTIFIER_KEY: 'degen1'},
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x80c008A7c9ec056158cB1F64024e710C8398048A']])
def test_claim_airdrop_3(
        base_accounts: list[ChecksumEvmAddress],
        base_transaction_decoder: BaseTransactionDecoder,
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x40920bf5416e9bd756d1c57f04e1b978e838efb42e7c2b07c4e9aaa8eb0da2ef ')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1715696797000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000016768741928411'),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=121,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=DEGEN_TOKEN,
            amount=FVal(claimed_amount := '1649'),
            location_label=user_address,
            counterparty=CPT_DEGEN,
            address=CLAIM_AIRDROP_3_CONTRACT,
            notes=f'Claim {claimed_amount} DEGEN from Degen airdrop 3',
            extra_data={AIRDROP_IDENTIFIER_KEY: 'degen2_season3'},
        ),
    ]
