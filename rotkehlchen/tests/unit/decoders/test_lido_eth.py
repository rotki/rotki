from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.lido.constants import CPT_LIDO, WITHDRAWAL_QUEUE
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4C49d4Bd6a571827B4A556a0e1e3071DA6231B9D']])
def test_lido_steth_staking(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x23a3ee601475424e91bdc0999a780afe57bf37cbcce6d1c09a4dfaaae1765451')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1710486191000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002846110430778206'),
            location_label=ethereum_accounts[0],
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount_deposited := '1.12137397'),
            location_label=ethereum_accounts[0],
            notes=f'Submit {amount_deposited} ETH to Lido',
            counterparty=CPT_LIDO,
            address=A_STETH.resolve_to_evm_token().evm_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_STETH,
            amount=FVal(amount_minted := '1.121373969999999999'),
            location_label=ethereum_accounts[0],
            notes=f'Receive {amount_minted} stETH in exchange for the deposited ETH',
            counterparty=CPT_LIDO,
            address=ZERO_ADDRESS,
            extra_data={'staked_eth': str(amount_deposited)},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4F243B4b795502AA5Cf562cB42EccD444c0321b0']])
def test_lido_wsteth_wrapping(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x21e291c980e6ca90b6b52bf13bc43c26bead4d3129bdbc463e140592294fe5bd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1733619851000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00117399752663733'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=322,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_STETH,
        amount=ZERO,
        location_label=user_address,
        address=A_WSTETH.resolve_to_evm_token().evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=323,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_STETH,
        amount=FVal(amount_steth := '26.235763844022460916'),
        location_label=user_address,
        notes=f'Wrap {amount_steth} stETH in {A_WSTETH.symbol_or_name()}',
        counterparty=CPT_LIDO,
        address=A_WSTETH.resolve_to_evm_token().evm_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=324,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_WSTETH,
        amount=FVal(amount_wsteth := '22.101307407211190709'),
        location_label=user_address,
        notes=f'Receive {amount_wsteth} wstETH after wrapping',
        counterparty=CPT_LIDO,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x29eC7360170367F86F4e18dA8Cf232A9C108Dc60']])
def test_lido_wsteth_unwrapping(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x104e9b227fb672dd32f3b9bfca002eec783846a6e8787010f6c0f5579f111ef1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1759185275000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000030746884486906'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_WSTETH,
        amount=FVal(amount_wsteth := '22.593785199529477044'),
        location_label=user_address,
        notes=f'Return {amount_wsteth} wstETH to be unwrapped',
        counterparty=CPT_LIDO,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_STETH,
        amount=FVal(amount_steth := '27.451978417858478677'),
        location_label=user_address,
        notes=f'Unwrap {amount_steth} stETH',
        counterparty=CPT_LIDO,
        address=A_WSTETH.resolve_to_evm_token().evm_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1F4bd8875Fb95B53492eE2075623526B0234BD45']])
def test_lido_withdrawal_request(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x58113538543f85dd41812643724a43cac2aec5b1584266dc4532329c513f7d82')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1793102807000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000036982566739171'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=296,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=ZERO,
            location_label=user_address,
            address=WITHDRAWAL_QUEUE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=297,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_STETH,
            amount=FVal(amount := '0.004999999999999999'),
            location_label=user_address,
            notes=f'Request withdrawal of {amount} stETH from Lido',
            counterparty=CPT_LIDO,
            address=WITHDRAWAL_QUEUE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=300,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc721:0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1/139838'),
            amount=ONE,
            location_label=user_address,
            notes=f'Receive Lido: stETH Withdrawal NFT with id 139838 from {ZERO_ADDRESS} to {user_address}',  # noqa: E501
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x135f26768811A5100d7B0Fe1BC0bfadb2Cff6259']])
def test_lido_withdrawal_claim(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8468d972dba60d05295f1f2ae8cb2b5807f90cb78f4b7d65c912bb81ff928f52')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1793103311000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000003556506483978'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount := '1.02237800489562768'),
            location_label=user_address,
            notes=f'Claim {amount} ETH from Lido withdrawal',
            counterparty=CPT_LIDO,
            address=WITHDRAWAL_QUEUE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=732,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc721:0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1/139515'),
            amount=ONE,
            location_label=user_address,
            notes=f'Send Lido: stETH Withdrawal NFT with id 139515 from {user_address} to {ZERO_ADDRESS}',  # noqa: E501
            address=ZERO_ADDRESS,
        ),
    ]
