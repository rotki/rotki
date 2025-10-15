from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.extrafi.decoder import (
    CPT_EXTRAFI,
    EXTRAFI_FARMING_CONTRACT,
    EXTRAFI_POOL_CONTRACT,
    EXTRAFI_STAKING_CONTRACT,
    VOTE_ESCROW,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.extrafi.constants import EXTRAFI_COMMUNITY_FUND
from rotkehlchen.constants.assets import A_ETH, A_OP
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4ba257EC214BA1e6a3b4E46Bd7C4654b9E81CED3']])
def test_extrafi_deposit_and_stake(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x81a87d2f8a9752ac4889ec92d6ec553417e3b4cc709a240718cf423f362e89b1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, deposited_amount = TimestampMS(1724325113000), '0.000000295568286412', '3259.807132247307892938'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal('10180971820322352348298.271714677763401611'),
            location_label=optimism_accounts[0],
            notes=f'Set VELO spending approval of 0x4ba257EC214BA1e6a3b4E46Bd7C4654b9E81CED3 by {EXTRAFI_POOL_CONTRACT} to 10180971820322352348298.271714677763401611',  # noqa: E501
            address=EXTRAFI_POOL_CONTRACT,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal(deposited_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {deposited_amount} VELO into Extrafi lend',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0xC89Bddb6E5aada6Ef9e15eeA77E9C5e0dB9dAe5D'),
            extra_data={'reserve_index': 35},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x92c90a4eA6F205dEe545ac348bBF005C4a019c78']])
def test_extrafi_unstake_and_withdraw(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x6acaea14d49f1e27902064251b1656067ed2518f831ae2d75ca6806bb7a21892')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, deposited_amount = TimestampMS(1724414161000), '0.00000029164013947', '28996.716869'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
            amount=FVal(deposited_amount),
            location_label=optimism_accounts[0],
            notes=f'Withdraw {deposited_amount} USDC from Extrafi lend',
            address=string_to_evm_address('0x85B16A35d310Db338D7bA35b85F83ea44182A396'),
            counterparty=CPT_EXTRAFI,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x7C16C022048b25142482CF06AC98064527395290']])
def test_extrafi_claim_from_pool(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x0c14b9d8d9a7dbe9243a29f4ec4d32852456163f80f46de7119c2c9fd8737a0b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, claimed_extra, claimed_op = TimestampMS(1717599275000), '0.000012215355410845', '42.0693742435086256', '0.162673580112061904'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=FVal(claimed_extra),
            location_label=optimism_accounts[0],
            notes=f'Claim {claimed_extra} EXTRA from Extrafi',
            counterparty=CPT_EXTRAFI,
            address=EXTRAFI_STAKING_CONTRACT,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=20,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_OP,
            amount=FVal(claimed_op),
            location_label=optimism_accounts[0],
            notes=f'Claim {claimed_op} OP from Extrafi',
            counterparty=CPT_EXTRAFI,
            address=EXTRAFI_STAKING_CONTRACT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xfE9182CD69F9fEb2A22C8bB88D03dCBBDfF77f11']])
def test_extrafi_lock_token(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x10cc6bb6d749e4c42c4d961de69bcd0d3885fe74ecc627e9069b41d000344fa7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, locked_amount = TimestampMS(1724678695000), '0.000002162513212219', '10077.656075837376207314'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=ZERO,
            location_label=optimism_accounts[0],
            notes=f'Revoke EXTRA spending approval of 0xfE9182CD69F9fEb2A22C8bB88D03dCBBDfF77f11 by {VOTE_ESCROW}',  # noqa: E501
            address=VOTE_ESCROW,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=FVal(locked_amount),
            location_label=optimism_accounts[0],
            notes=f'Lock {locked_amount} EXTRA until 21/08/2025 00:00:00',
            counterparty=CPT_EXTRAFI,
            address=VOTE_ESCROW,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4003eeb8e27D300c8420ecDeDfB96C4dE7a46E7E']])
def test_extrafi_repay(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xc1b3c8ac33f3b5d27e48377e59a6a6c384ee425f86c7ac86cec4b903e38c9bca')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, repaid_amount, refund_amount = TimestampMS(1722746575000), '0.000001297692870133', '0.001369169723826962', '0.000000000000000002'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_ETH,
            amount=FVal(repaid_amount),
            location_label=optimism_accounts[0],
            notes=f'Repay {repaid_amount} ETH in Extrafi EXA-WETH farm',
            address=EXTRAFI_FARMING_CONTRACT,
            counterparty=CPT_EXTRAFI,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=A_ETH,
            amount=FVal(refund_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {refund_amount} ETH as refund from Extrafi',
            counterparty=CPT_EXTRAFI,
            address=EXTRAFI_FARMING_CONTRACT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x225170393fCD06F3295aDa2bF33002C8ec94b8E4']])
def test_extrafi_repay_with_token(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x5b907d75ec3ba70436385071fc57e31b428b24cb92a05d802a5714273171e697')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, repaid_amount, refund_amount = TimestampMS(1721340039000), '0.000076904200008685', '1589.9698', '0.000002'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=44,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal('115792089237316195423570985008687907853269984665640564039457584007873814.838605'),
            location_label=optimism_accounts[0],
            notes=f'Set USDC.e spending approval of {optimism_accounts[0]} by 0xf9cFB8a62f50e10AdDE5Aa888B44cF01C5957055 to 115792089237316195423570985008687907853269984665640564039457584007873814.838605',  # noqa: E501
            address=EXTRAFI_FARMING_CONTRACT,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=45,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(repaid_amount),
            location_label=optimism_accounts[0],
            notes=f'Repay {repaid_amount} USDC.e in Extrafi USDC.e-wUSDR farm',
            address=string_to_evm_address('0x5f88d6f7beD0538Ca825404Baf20C846b4073e5D'),
            counterparty=CPT_EXTRAFI,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=46,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REFUND,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(refund_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {refund_amount} USDC.e as refund from Extrafi',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0x5f88d6f7beD0538Ca825404Baf20C846b4073e5D'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4003eeb8e27D300c8420ecDeDfB96C4dE7a46E7E']])
def test_close_position(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x24c5e37be0340c3713c851cbe849f2f2d7c9fd9c776d889fe065cd5aaaadb49f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, withdrawn_amount = TimestampMS(1722759379000), '0.000001936939279642', '6.195522513842170302'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=96,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:10/erc20:0x1e925De1c68ef83bD98eE3E130eF14a50309C01B'),
            amount=FVal(withdrawn_amount),
            location_label=optimism_accounts[0],
            notes=f'Withdraw {withdrawn_amount} EXA from Extrafi EXA-WETH farm',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0x9558FF42E95dcA076A8DEB67c8FF8B86f52b2f8C'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4003eeb8e27D300c8420ecDeDfB96C4dE7a46E7E']])
def test_farm_investment(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xf1f2de24757b57df7b53090369020a527f9ea54d5a876fe85fe972643c50a7e2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, fee_amount, deposited_amount, borrow_amount = TimestampMS(1722792861000), '0.000027486262250944', '8.230157245731733013', '0.002920375680424896'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=48,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x1e925De1c68ef83bD98eE3E130eF14a50309C01B'),
            amount=FVal(2),
            location_label=optimism_accounts[0],
            notes=f'Set EXA spending approval of 0x4003eeb8e27D300c8420ecDeDfB96C4dE7a46E7E by {EXTRAFI_FARMING_CONTRACT} to 2',  # noqa: E501
            address=EXTRAFI_FARMING_CONTRACT,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=49,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x1e925De1c68ef83bD98eE3E130eF14a50309C01B'),
            amount=FVal(deposited_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {deposited_amount} EXA in Extrafi EXA-WETH farm',
            counterparty=CPT_EXTRAFI,
            extra_data={'vault_id': 70, 'vault_position': 511},
            address=string_to_evm_address('0x9558FF42E95dcA076A8DEB67c8FF8B86f52b2f8C'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=50,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=Asset('eip155:10/erc20:0x4200000000000000000000000000000000000006'),
            amount=FVal(borrow_amount),
            location_label=optimism_accounts[0],
            notes=f'Borrow {borrow_amount} WETH in Extrafi EXA-WETH farm',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0xf9cFB8a62f50e10AdDE5Aa888B44cF01C5957055'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=51,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x4200000000000000000000000000000000000006'),
            amount=FVal(borrow_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {borrow_amount} WETH in Extrafi EXA-WETH farm',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0xf9cFB8a62f50e10AdDE5Aa888B44cF01C5957055'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x007183900fBbe3e7815b278074a49B8C7319EDba']])
def test_new_farm_borrow_position_on_base(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0xb9479f2e21100ddbba10395d76abb2fb4e151b2142ba90c91151a10fcb5cfbc7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash)
    timestamp, borrow_amount, gas_fees = TimestampMS(1725972969000), '4025.689364', '0.000006907473477667'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=base_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            amount=FVal(borrow_amount),
            location_label=base_accounts[0],
            notes=f'Borrow {borrow_amount} USDC in Extrafi USDz-USDC farm',
            counterparty=CPT_EXTRAFI,
            address=EXTRAFI_FARMING_CONTRACT,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
            amount=FVal(borrow_amount),
            location_label=base_accounts[0],
            notes=f'Deposit {borrow_amount} USDC in Extrafi USDz-USDC farm',
            counterparty=CPT_EXTRAFI,
            address=EXTRAFI_FARMING_CONTRACT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x007183900fBbe3e7815b278074a49B8C7319EDba']])
def test_new_farm_position_on_base(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0xf0458b2c208fa7362669b6430277808a2bda527fcbe5dd3514a5879c445311cc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash)
    timestamp, deposit_amount, gas_fees = TimestampMS(1725309783000), '5042.114438', '0.000003258939143014'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=base_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=390,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:8453/erc20:0xB79DD08EA68A908A97220C76d19A6aA9cBDE4376'),
            amount=FVal(deposit_amount),
            location_label=base_accounts[0],
            notes=f'Deposit {deposit_amount} USD+ in Extrafi OVN-USD+ farm',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0x88F6e275dD40250782ff48c9b561C8a875934043'),
            extra_data={'vault_id': 20, 'vault_position': 3408},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xDbA7bB7Ee25d259e0a14880Ef107A7c5106A716d']])
def test_vested_extra_base(base_inquirer, base_accounts):
    evmhash = deserialize_evm_tx_hash('0x560a5e279a7f1b9c89dca3d7f93da11c9418037c0362f01b443d50967a719d5d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=evmhash)
    timestamp, locked_amount, gas_fees = TimestampMS(1722581379000), '8.004925206880061111', '0.000002859618316575'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=base_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=53,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:8453/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=ZERO,
            location_label=base_accounts[0],
            notes=f'Revoke EXTRA spending approval of {base_accounts[0]} by 0xe0BeC4F45aEF64CeC9dCB9010d4beFfB13e91466',  # noqa: E501
            address=VOTE_ESCROW,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=54,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:8453/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=FVal(locked_amount),
            location_label=base_accounts[0],
            notes=f'Lock {locked_amount} EXTRA until 08/08/2024 00:00:00',
            counterparty=CPT_EXTRAFI,
            address=VOTE_ESCROW,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_EXTRAFI]])
@pytest.mark.parametrize('optimism_accounts', [['0x35d527C6aF6621DFc46f7CcCE92948d49CF1Fe27']])
def test_extrafi_claim_lending(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x6cca377983ebf715d83a3ea566e420d79abf545b8aad61c6bad68cc60fc57c05')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, fee_amount, claimed_extra, claimed_op = TimestampMS(1727429719000), '0.000000266809434775', '8.888980847307437249', '0.137614520893025687'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=optimism_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=41,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:10/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=FVal(claimed_extra),
            location_label=optimism_accounts[0],
            notes=f'Claim {claimed_extra} EXTRA from Extrafi lending',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0x5DC1a8Fa98508e342FA8CFf0c49ab57138d53337'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=43,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_OP,
            amount=FVal(claimed_op),
            location_label=optimism_accounts[0],
            notes=f'Claim {claimed_op} OP from Extrafi lending',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0x5DC1a8Fa98508e342FA8CFf0c49ab57138d53337'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_EXTRAFI]])
@pytest.mark.parametrize('base_accounts', [['0x8887a050A8c6873c9cA7553e3F7Bfb0e9b36AEE1']])
def test_extrafi_claim_lending_base(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0xccefe09c6b3cfc9753494c28f07de309d26ccb5169ed478c93b4169776ac0edc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, fee_amount, claimed_extra = TimestampMS(1721419937000), '0.000001803922832983', '6.970955942301511307'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=base_accounts[0],
            notes=f'Burn {fee_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=284,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
            amount=FVal(claimed_extra),
            location_label=base_accounts[0],
            notes=f'Claim {claimed_extra} EXTRA from Extrafi lending',
            counterparty=CPT_EXTRAFI,
            address=string_to_evm_address('0x79a5a9e97Dc8f4a1c2370E1049dB960275431793'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x0EdB39ada48BDF162C09983e0005825c4ce3E5B4']])
def test_op_incentive_rewards(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xb9bb665425a4beeac4afaba637bffcdfc3fe57d2606eee44ec90bba532050a0c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, amount = TimestampMS(1737018755000), '0.769886891'
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=58,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_OP,
            amount=FVal(amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {amount} OP as a reward incentive for participating in an Extrafi pool',  # noqa: E501
            counterparty=CPT_EXTRAFI,
            address=EXTRAFI_COMMUNITY_FUND,
        ),
    ]
