from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.kiln.constants import KILN_VPOOL_BEACON
from rotkehlchen.chain.ethereum.modules.kiln.decoder import KilnDecoder
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.kiln.constants import CPT_KILN
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

LEDGER_INTEGRATION = string_to_evm_address('0x5DB5235b5C7e247488784986e58019fFFd98FdA4')
KILN_EXIT_QUEUE = string_to_evm_address('0x8d6Fd650500f82c7D978a440348e5a9b886943bF')
A_PSETH = Asset(f'eip155:1/erc20:{LEDGER_INTEGRATION}')


def _ticket(ticket_id: str) -> Asset:
    return Asset(f'eip155:1/erc721:{KILN_EXIT_QUEUE}/{ticket_id}')


def _stake_events(user_address: ChecksumEvmAddress) -> list[EvmEvent]:
    return [EvmEvent(
        tx_ref=(tx_hash := deserialize_evm_tx_hash('0xff21c101966941bb6cc0a696ee1e7fd83a784b31b458893befab7b649673c351')),  # noqa: E501
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1793812319000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000054191246010005'),
        location_label=user_address,
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(staked_amount := '0.1681'),
        location_label=user_address,
        notes=f'Stake {staked_amount} ETH in Kiln',
        counterparty=CPT_KILN,
        address=LEDGER_INTEGRATION,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_PSETH,
        amount=FVal(received_amount := '0.154433631443575568'),
        location_label=user_address,
        notes=f'Receive {received_amount} psETH from staking in Kiln',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    )]


def _claim_events(user_address: ChecksumEvmAddress) -> list[EvmEvent]:
    return [EvmEvent(
        tx_ref=(tx_hash := deserialize_evm_tx_hash('0x0efc236e03b6cc96d04d53182c11a4144083bc680f68681b526e4b483b42855c')),  # noqa: E501
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1793494259000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000094811314722425'),
        location_label=user_address,
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=_ticket(ticket_id := '30721032367989245419936923681457223415523681'),
        amount=ONE,
        location_label=user_address,
        notes=f'Return Kiln exit ticket {ticket_id}',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(claimed_amount := '0.802229449357201022'),
        location_label=user_address,
        notes=f'Claim {claimed_amount} ETH from Kiln exit queue',
        counterparty=CPT_KILN,
        address=KILN_EXIT_QUEUE,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC89B0dD4d20febdBFeD2f733B5687780AebcD42E']])
def test_kiln_stake(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xff21c101966941bb6cc0a696ee1e7fd83a784b31b458893befab7b649673c351'),
    )
    assert events == _stake_events(ethereum_accounts[0])
    assert A_PSETH.resolve_to_evm_token().protocol == CPT_KILN


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xaebF8c5b3E89369e3819B8F307A0b628994E2020']])
def test_kiln_request_exit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x04d9c648cf7239957c891a3d3de752165477bd8964247644475d8d3e3c11253d')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1793818295000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000072592448159012'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_PSETH,
        amount=FVal(burned_amount := '0.932473003801038413'),
        location_label=user_address,
        notes=f'Request exit of {burned_amount} psETH worth {(max_exitable := "1.014990779364175186")} ETH from Kiln',  # noqa: E501
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
        extra_data={'tickets': [{
            'exit_queue': KILN_EXIT_QUEUE,
            'ticket_id': (ticket_id := '37841781178176803706371500890418558458384733'),
        }]},
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=_ticket(ticket_id),
        amount=ONE,
        location_label=user_address,
        notes=f'Receive Kiln exit ticket {ticket_id} for up to {max_exitable} ETH',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9Da0F59EdF6A88ED3AFb4d21e3373199757eB90B']])
def test_kiln_claim(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x0efc236e03b6cc96d04d53182c11a4144083bc680f68681b526e4b483b42855c'),
    )
    assert events == _claim_events(ethereum_accounts[0])


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4aAD64bcBD051f8a845356E1B51b42EDAbE9440F']])
def test_kiln_partial_claim_via_helper(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Two tickets claimed via the Kiln claim helper in one payment. The second one is
    only partially funded, so it is burned and re-issued for the remainder."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x6419ca26c9f99c1beb9eb6e89859a974a1303ce8558e56f9cc557a91d4c7081a')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1730303735000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.005762800448324128'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=_ticket(first_id := '11221491613951787709631797961770614179874617'),
        amount=ONE,
        location_label=user_address,
        notes=f'Return Kiln exit ticket {first_id}',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=_ticket(second_id := '11410348327592908556854358734326890221214127'),
        amount=ONE,
        location_label=user_address,
        notes=f'Return Kiln exit ticket {second_id}',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=_ticket(reissued_id := '11410348327592908556854308731135129090724953'),
        amount=ONE,
        location_label=user_address,
        notes=f'Receive Kiln exit ticket {reissued_id} for the unclaimed remainder of a partially claimed ticket',  # noqa: E501
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(claimed_amount := '149.057500420405616104'),
        location_label=user_address,
        notes=f'Claim {claimed_amount} ETH from Kiln exit queue',
        counterparty=CPT_KILN,
        address=KILN_EXIT_QUEUE,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xC89B0dD4d20febdBFeD2f733B5687780AebcD42E',
    '0x9Da0F59EdF6A88ED3AFb4d21e3373199757eB90B',
]])
def test_kiln_unlisted_contracts(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Integration contracts and exit queues that are not hardcoded are detected by the
    decoding rule via their beacon and decoded the same way as the hardcoded ones."""
    with (
        patch('rotkehlchen.chain.ethereum.modules.kiln.decoder.KILN_INTEGRATION_CONTRACTS', new=set()),  # noqa: E501
        patch('rotkehlchen.chain.ethereum.modules.kiln.decoder.KILN_EXIT_QUEUES', new=set()),
    ):
        stake_events, decoder = get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            tx_hash=deserialize_evm_tx_hash('0xff21c101966941bb6cc0a696ee1e7fd83a784b31b458893befab7b649673c351'),
        )
        claim_events, _ = get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            tx_hash=deserialize_evm_tx_hash('0x0efc236e03b6cc96d04d53182c11a4144083bc680f68681b526e4b483b42855c'),
            evm_decoder=decoder,
        )

    assert stake_events == _stake_events(ethereum_accounts[0])
    assert claim_events == _claim_events(ethereum_accounts[1])
    assert isinstance(kiln_decoder := decoder.decoders['Kiln'], KilnDecoder)
    assert kiln_decoder.integration_checks == {LEDGER_INTEGRATION: True}
    assert kiln_decoder.exit_queue_checks == {KILN_EXIT_QUEUE: True}


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC89B0dD4d20febdBFeD2f733B5687780AebcD42E']])
def test_kiln_contract_verification(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Contracts that are not Kiln ones are rejected and the result is cached"""
    _, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xff21c101966941bb6cc0a696ee1e7fd83a784b31b458893befab7b649673c351'),
    )
    assert isinstance(kiln_decoder := decoder.decoders['Kiln'], KilnDecoder)
    weth_address = A_WETH.resolve_to_evm_token().evm_address
    assert kiln_decoder._is_kiln_integration(weth_address) is False  # no pools()
    assert kiln_decoder._is_kiln_integration(KILN_VPOOL_BEACON) is False
    assert kiln_decoder._is_kiln_exit_queue(weth_address) is False
    assert kiln_decoder._is_kiln_integration(LEDGER_INTEGRATION) is True
    assert kiln_decoder.integration_checks == {
        weth_address: False,
        KILN_VPOOL_BEACON: False,
        LEDGER_INTEGRATION: True,
    }
    assert kiln_decoder.exit_queue_checks == {weth_address: False}
