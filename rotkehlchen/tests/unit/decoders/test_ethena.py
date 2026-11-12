from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.ethena.constants import (
    CPT_ETHENA,
    ENA_SILO,
    SENA_ADDRESS,
    SUSDE_ADDRESS,
    USDE_SILO,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

A_USDE = Asset('eip155:1/erc20:0x4c9EDD5852cd905f086C759E8383e09bff1E68B3')
A_SUSDE = Asset('eip155:1/erc20:0x9D39A5DE30e57443BfF2A8307A4256c8797A3497')
A_ENA = Asset('eip155:1/erc20:0x57e114B691Db790C35207b2e685D4A43181e6061')
A_SENA = Asset('eip155:1/erc20:0x8bE3460A480c80728a8C4D7a5D5303c85ba7B3b9')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb4EeDf471989abfbBaCbD368E643d481Af7375aC']])
def test_stake_usde(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7e4a55d291aee90c998cbeb555c66063e6d281b6576c68e54e71628e121455dd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794446411000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000057596234856056'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=407,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDE,
        amount=FVal(0),
        location_label=user_address,
        address=SUSDE_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=408,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_USDE,
        amount=FVal(staked_amount := '34659.648303995662472935'),
        location_label=user_address,
        notes=f'Stake {staked_amount} USDe in Ethena',
        counterparty=CPT_ETHENA,
        address=SUSDE_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=409,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_SUSDE,
        amount=FVal(received_amount := '27556.135896513229967769'),
        location_label=user_address,
        notes=f'Receive {received_amount} sUSDe after staking in Ethena',
        counterparty=CPT_ETHENA,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2a50a100B1d16950cc6DC637661C41Fc60Ad8554']])
def test_cooldown_susde(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x37827f93aeeaaf7447d011cbf0f410390af99326fee03d2ea0da4aee341934e2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794435263000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000067707109426349'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=330,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_SUSDE,
        amount=FVal(returned_amount := '118000'),
        location_label=user_address,
        notes=f'Return {returned_amount} sUSDe to Ethena and start the cooldown to unstake 148415.866652059675766604 USDe',  # noqa: E501
        counterparty=CPT_ETHENA,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb4EeDf471989abfbBaCbD368E643d481Af7375aC']])
def test_unstake_usde(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x711e9a4147651fe74bcb038ae0ebd3ce13a6c5644b7a228d1f815bbe7141391e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794445523000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000039397553928548'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=327,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_USDE,
        amount=FVal(unstaked_amount := '32786.23368930067686022'),
        location_label=user_address,
        notes=f'Unstake {unstaked_amount} USDe from Ethena after the cooldown',
        counterparty=CPT_ETHENA,
        address=USDE_SILO,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x31B7d5A2B1CE1871Dd642F6aeCC0Ef68d126B95A']])
def test_unstake_usde_from_safe(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Unstake called through a Safe, which also bridges the USDe in the same transaction"""
    tx_hash = deserialize_evm_tx_hash('0x2129fc847191358052aedb42c667077d4815e7100128d048b140f77af18742c4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794386723000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(refund_amount := '0.000048654649892616'),
        location_label=(safe_address := ethereum_accounts[0]),
        notes=f'Receive {refund_amount} ETH from {(relayer := string_to_evm_address("0x1a44076050125825900e736c501f859c50fE728c"))}',  # noqa: E501
        address=relayer,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('0.0004'),
        location_label=safe_address,
        notes=f'Send 0.0004 ETH to {(usde_oft_adapter := string_to_evm_address("0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34"))}',  # noqa: E501
        address=usde_oft_adapter,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1653,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_USDE,
        amount=FVal(unstaked_amount := '3143708.384849872961199482'),
        location_label=safe_address,
        notes=f'Unstake {unstaked_amount} USDe from Ethena after the cooldown',
        counterparty=CPT_ETHENA,
        address=USDE_SILO,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1654,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDE,
        amount=FVal(unstaked_amount),
        location_label=safe_address,
        address=usde_oft_adapter,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1655,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDE,
        amount=FVal('0.000000872961199482'),
        location_label=safe_address,
        address=usde_oft_adapter,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1656,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_USDE,
        amount=FVal(bridged_amount := '3143708.384849'),
        location_label=safe_address,
        notes=f'Send {bridged_amount} USDe from {safe_address} to {usde_oft_adapter}',
        address=usde_oft_adapter,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5f7C30CedE26106D06fc0a777F492Ef5925a1A90']])
def test_stake_ena(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb5b36388d89966d87749ec0fb4ee19b3fc72a8d6153de3cb25970a5284c8a05e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794429875000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000026405144850013'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ENA,
        amount=FVal(staked_amount := '6702.390613052804694509'),
        location_label=user_address,
        notes=f'Stake {staked_amount} ENA in Ethena',
        counterparty=CPT_ETHENA,
        address=SENA_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_SENA,
        amount=FVal(received_amount := '6582.13919245069105172'),
        location_label=user_address,
        notes=f'Receive {received_amount} sENA after staking in Ethena',
        counterparty=CPT_ETHENA,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x95B8Ec85A3d5dE4985D11A8ea028B52DBA52afCc']])
def test_cooldown_sena(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf8b811f6a4224f0dc7878799caa5f52ecc97ae671f9bba881acc04e7a97ce9cb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794445955000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00000888444'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=610,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_SENA,
        amount=FVal(returned_amount := '11435.818000779471531265'),
        location_label=user_address,
        notes=f'Return {returned_amount} sENA to Ethena and start the cooldown to unstake 11644.742990077509148644 ENA',  # noqa: E501
        counterparty=CPT_ETHENA,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5f7C30CedE26106D06fc0a777F492Ef5925a1A90']])
def test_unstake_ena(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8ae20b106e0ce412b9867705c27fabb175e00dc10e86425c2b98e70bcdd8cf0f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794429827000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000039880654877829'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=669,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ENA,
        amount=FVal(unstaked_amount := '21.724943331908931386'),
        location_label=user_address,
        notes=f'Unstake {unstaked_amount} ENA from Ethena after the cooldown',
        counterparty=CPT_ETHENA,
        address=ENA_SILO,
    )]
