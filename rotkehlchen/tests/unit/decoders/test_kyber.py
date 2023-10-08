import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.kyber.constants import CPT_KYBER
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_CRV, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6d379cb5BA04c09293b21Bf314E7aba3FfEAaF5b']])
def test_kyber_legacy_old_contract(database, ethereum_inquirer, ethereum_accounts):
    """
    Data for trade taken from
    https://etherscan.io/tx/0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87
    """
    tx_hex = deserialize_evm_tx_hash('0xe9cc9f27ef2a09fe23abc886a0a0f7ae19d9e2eb73663e1e41e07a3e0c011b87')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )

    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=1591043988000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.01212979988),
                usd_value=ZERO,
            ),
            location_label=ethereum_accounts[0],
            notes='Burned 0.01212979988 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=1591043988000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal(45), usd_value=ZERO),
            location_label=ethereum_accounts[0],
            notes='Swap 45 USDC in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=1591043988000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal('0.187603293406027635'),
                usd_value=ZERO,
            ),
            location_label=ethereum_accounts[0],
            notes='Receive 0.187603293406027635 ETH from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0']])
def test_kyber_legacy_new_contract(database, ethereum_inquirer):
    """Data for trade taken from
    https://etherscan.io/tx/0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22
    """
    tx_hex = deserialize_evm_tx_hash('0xe80928d5e21f9628c047af1f8b191cbffbb6b8b9945adb502cfb3af152552f22')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )

    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=1644182638000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.066614401),
                usd_value=ZERO,
            ),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Burned 0.066614401 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=1644182638000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal(8139.77872), usd_value=ZERO),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Swap 8139.77872 USDC in kyber',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x7C66550C9c730B6fdd4C03bc2e73c5462c5F7ACC'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=1644182638000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_CRV,
            balance=Balance(amount=FVal('2428.33585390706162556'), usd_value=ZERO),
            location_label='0x5340F6faff9BF55F66C16Db6Bf9E020d987F87D0',
            notes='Receive 2428.33585390706162556 CRV from kyber swap',
            counterparty=CPT_KYBER,
            address=string_to_evm_address('0x7C66550C9c730B6fdd4C03bc2e73c5462c5F7ACC'),
        ),
    ]
    assert events == expected_events
