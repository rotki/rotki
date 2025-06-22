import pytest

from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH, A_LQTY
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import LIQUITY_STAKING_DETAILS, EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD77Eb80F38fEC10D87A192d07329415173307E93']])
def test_lqty_v2_staking_deposit_with_rewards(ethereum_inquirer, ethereum_accounts):
    """Test Liquity V2 staking deposit transaction that also claims previous rewards"""
    evmhash = deserialize_evm_tx_hash('0x80d85ccacbc3acdbc797ed580044c0d5427d19f70d9d1b67d724bdc7bd4aeff8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=evmhash)
    timestamp = TimestampMS(1750380179000)

    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000106660179104193'),
            location_label=ethereum_accounts[0],
            notes='Burn 0.000106660179104193 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=279,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_LQTY,
            amount=FVal('0'),
            location_label=ethereum_accounts[0],
            notes='Revoke LQTY spending approval of 0xD77Eb80F38fEC10D87A192d07329415173307E93 by 0x3Dd5BbB839f8AE9B64c73780e89Fdd1181Bf5205',  # noqa: E501
            counterparty=None,
            address='0x3Dd5BbB839f8AE9B64c73780e89Fdd1181Bf5205',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=280,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LQTY,
            amount=FVal('1742.012204302870975901'),
            location_label=ethereum_accounts[0],
            notes='Stake 1742.012204302870975901 LQTY in the Liquity V2 protocol',
            counterparty=CPT_LIQUITY,
            address='0x3Dd5BbB839f8AE9B64c73780e89Fdd1181Bf5205',
            extra_data={
                LIQUITY_STAKING_DETAILS: {
                    'staked_amount': '52907.46069202884604981',
                    'asset': 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D',
                },
            },
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=281,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            amount=FVal('1.125295810448450699'),
            location_label=ethereum_accounts[0],
            notes="Collect 1.125295810448450699 LQTY from Liquity's stability pool into the user's Liquity proxy",  # noqa: E501
            counterparty=CPT_LIQUITY,
            address='0x807DEf5E7d057DF05C796F4bc75C3Fe82Bd6EeE1',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=282,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            amount=FVal('0.000086401749307711'),
            location_label=ethereum_accounts[0],
            notes="Collect 0.000086401749307711 ETH from Liquity's stability pool into the user's Liquity proxy",  # noqa: E501
            counterparty=CPT_LIQUITY,
            address='0x807DEf5E7d057DF05C796F4bc75C3Fe82Bd6EeE1',
        ),
    ]
    assert events == expected_events
