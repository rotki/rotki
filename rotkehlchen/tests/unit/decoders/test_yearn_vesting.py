from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.yearn.vesting.constants import (
    CPT_YEARN_VESTING,
    VYPER_DONATION_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_YFI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52']])
def test_vesting_escrow_creation(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test the funder side decoding of a v0.3.0 factory vesting escrow deployment"""
    tx_hash = deserialize_evm_tx_hash('0x4a95c820e82f7677a33298c1ecba4079e8a94ce8ad2f260e8fba5708dd1cdf83')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    yvdai = Asset('eip155:1/erc20:0x028eC7330ff87667b6dfb0D94b954c820195336c')
    escrow = string_to_evm_address('0x9b1B5ddE32cDE7a53D1c70A9f30130547424d781')
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1730212319000)
    assert events == [
        EvmEvent(
            sequence_index=94,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=yvdai,
            amount=FVal(received_amount := '61352.174049471814839136'),
            location_label=user_address,
            notes=f'Receive {received_amount} yvDAI-1 from 0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde to {user_address}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde'),
        ), EvmEvent(
            sequence_index=95,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=yvdai,
            amount=FVal(approval_amount := '61352.174049471814839136'),
            location_label=user_address,
            notes=f'Set yvDAI-1 spending approval of {user_address} by 0x200C92Dd85730872Ab6A1e7d5E40A067066257cF to {approval_amount}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF'),
        ), EvmEvent(
            sequence_index=96,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=yvdai,
            amount=FVal(approval_amount_2 := '607.44755577728393329'),
            location_label=user_address,
            notes=f'Set yvDAI-1 spending approval of {user_address} by 0x200C92Dd85730872Ab6A1e7d5E40A067066257cF to {approval_amount_2}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF'),
        ), EvmEvent(
            sequence_index=97,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=yvdai,
            amount=FVal(deposit_amount := '60744.726493694530905846'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} yvDAI-1 in a Yearn vesting escrow for 0x28eD70032Adc7575d45A0869CfDcCEcdE88C1a74 vesting until 30/11/2024 00:00:00',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=escrow,
            extra_data={'recipient': '0x28eD70032Adc7575d45A0869CfDcCEcdE88C1a74'},
        ), EvmEvent(
            sequence_index=98,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=yvdai,
            amount=FVal(approval_amount_3 := '0.000290840338624232'),
            location_label=user_address,
            notes=f'Set yvDAI-1 spending approval of {user_address} by 0x200C92Dd85730872Ab6A1e7d5E40A067066257cF to {approval_amount_3}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF'),
        ), EvmEvent(
            sequence_index=99,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=yvdai,
            amount=FVal(donation_amount := '607.447264936945309058'),
            location_label=user_address,
            notes=f'Donate {donation_amount} yvDAI-1 to the Vyper project',
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=VYPER_DONATION_ADDRESS,
        ), EvmEvent(
            sequence_index=101,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x7A1057E6e9093DA9C1D4C1D049609B6889fC4c67',
            notes=f'Successfully executed safe transaction 0x55c5905b51169a663e119127f434f2669853b74c48cdace0616eb4b67f1d15b9 for multisig {user_address}',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_SAFE_MULTISIG,
            address=user_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB1d693B77232D88a3C9467eD5619FfE79E80BCCc']])
def test_vesting_escrow_claim(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test decoding a claim of vested tokens from a v0.3.0 vesting escrow"""
    tx_hash = deserialize_evm_tx_hash('0xdbd01f5255ebdeffe7e609c9437a648c875d545b3f2ebfe9d74ed3e8cb384c8a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1698877619000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.00306796151931048'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=288,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_DAI,
            amount=FVal(claimed_amount := '6395.414351851851851851'),
            location_label=user_address,
            notes=f'Claim {claimed_amount} DAI from a Yearn vesting escrow',
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0xfDD74f49BDFeE0Af70Ffc6A556a2182380b40d32'),
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0x2D407dDb06311396fE14D4b49da5F0471447d45C']])
def test_vesting_escrow_claim_v1(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test decoding a claim from a v0.1.0 vesting escrow (YFI contributor vesting),
    which uses the older vyper forwarder proxy format.
    """
    tx_hash = deserialize_evm_tx_hash('0xc8ff00a7197eb9f9ffd84d5bf7c284eeab939696035751ae081ebc7ab144fc63')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1613502506000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.014004585'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=113,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_YFI,
            amount=FVal(claimed_amount := '53.860622516066294605'),
            location_label=user_address,
            notes=f'Claim {claimed_amount} YFI from a Yearn vesting escrow',
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0xB1A1Ae5c34CEec969E1f7e176fE8A0506CE044D6'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52']])
def test_vesting_escrow_rug_pull(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test decoding a rug pull of a v0.2.0 vesting escrow clawing back unvested YFI"""
    tx_hash = deserialize_evm_tx_hash('0x6c6eb67ad97dc06490bc9038c20ae40d0e6f13bfdda1e8d5bdb50e9a13b905fe')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1622679331000)
    assert events == [
        EvmEvent(
            sequence_index=42,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_YFI,
            amount=FVal(rugged_amount := '7.696550186030779639'),
            location_label=user_address,
            notes=f'Revoke the Yearn vesting escrow of 0x90e5aa59a9dF2ADd394df81521DbBEd5F3c4A1A3 clawing back {rugged_amount} YFI',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x8bc89738bCf37d43B05ad47079332e3aD2B82C4F'),
        ), EvmEvent(
            sequence_index=44,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x0Cec743b8CE4Ef8802cAc0e5df18a180ed8402A7',
            notes=f'Successfully executed safe transaction 0x029ab81fd0cbf4d7df032e2da128c9b2f3d27e3aa866024a02604c51f5f24cca for multisig {user_address}',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_SAFE_MULTISIG,
            address=user_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x57a8865cfB1eCEf7253c27da6B4BC3dAEE5Be518']])
def test_vesting_escrow_revoked(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test decoding a v0.3.0 vesting escrow revocation clawing back unvested GTC"""
    tx_hash = deserialize_evm_tx_hash('0xf3d7b596a889aa93f4f0b06ea5875a9022441a7b6de9a3e211ee865fdfd19aee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=151,
            timestamp=TimestampMS(1746294215000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=Asset('eip155:1/erc20:0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),
            amount=FVal(rugged_amount := '1128350.753900304414003045'),
            location_label=ethereum_accounts[0],
            notes=f'Revoke the Yearn vesting escrow of 0x74fEa3FB0eD030e9228026E7F413D66186d3D107 clawing back {rugged_amount} GTC',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x7DAE0a882bd4511fa6918e6A35B21aD31a89E3Ab'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4444AAAACDBa5580282365e25b16309Bd770ce4a']])
def test_vesting_escrow_set_open_claim(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test decoding a v0.3.0 escrow open claim toggle along a claim in the same
    transaction, by a recipient that is a safe multisig.
    """
    tx_hash = deserialize_evm_tx_hash('0x7a7f0053db287feff90628bb041f0e10a6d01b34168c97c1a2af9a13cf7620e9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1720832411000)
    assert events == [
        EvmEvent(
            sequence_index=161,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Disable permissionless claims of a Yearn vesting escrow',
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x29d0E623738fd93E60254c0D629f8dDeBD92aF40'),
        ), EvmEvent(
            sequence_index=164,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x2C2dc95F8C8060a7e3B354c1B9540881AEa1613C',
            notes=f'Successfully executed safe transaction 0x69a246b6d118f760b79e7d422307fd8ef2bccb8c82cdf664ac287917d05fd687 for multisig {user_address}',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_SAFE_MULTISIG,
            address=user_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFE11a5009f2121622271e7dd0FD470264e076af6']])
def test_vesting_escrow_disown(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test decoding a standalone renouncement of the revocation right of a v0.3.0
    escrow, done in the same transaction that deploys its replacement escrow.
    """
    tx_hash = deserialize_evm_tx_hash('0xaade17bb5fcb9d15867d8a8573b72e5306034da9ba6ffe866d86dc61c0c5c6e5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    rsup = Asset('eip155:1/erc20:0x419905009e4656fdC02418C7Df35B1E61Ed5F726')
    user_address, timestamp = ethereum_accounts[0], TimestampMS(1745610971000)
    assert events == [
        EvmEvent(
            sequence_index=145,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=rsup,
            amount=FVal(received_amount := '4549.5808845204568156'),
            location_label=user_address,
            notes=f'Receive {received_amount} RSUP from 0x4444444455bF42de586A88426E5412971eA48324 to {user_address}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x4444444455bF42de586A88426E5412971eA48324'),
        ), EvmEvent(
            sequence_index=148,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=rsup,
            amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640564039457.584007913129639935'),  # noqa: E501
            location_label=user_address,
            notes=f'Set RSUP spending approval of {user_address} by 0x200C92Dd85730872Ab6A1e7d5E40A067066257cF to {approval_amount}',  # noqa: E501
            tx_ref=tx_hash,
            address=string_to_evm_address('0x200C92Dd85730872Ab6A1e7d5E40A067066257cF'),
        ), EvmEvent(
            sequence_index=149,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=rsup,
            amount=FVal(deposit_amount := '4549.5808845204568156'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} RSUP in a Yearn vesting escrow for 0x80c9aC867b2D36B7e8D74646E074c460a008C0cb vesting until 30/07/2025 04:00:00',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x4aa944DfF7aadC4587C7c31Ad8b1867E5F43757b'),
            extra_data={'recipient': '0x80c9aC867b2D36B7e8D74646E074c460a008C0cb'},
        ), EvmEvent(
            sequence_index=151,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Renounce the right to revoke a Yearn vesting escrow',
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x3c89008Ae23fCF293DE3815A0a1e8E67e294e0CB'),
        ), EvmEvent(
            sequence_index=152,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x49e5097f627e400F2a377D5FD7E712d1E0e16FC2',
            notes=f'Successfully executed safe transaction 0x713bf823a8671f297fd98b4cecc408a7942185ed0330ed13f481dcfc4b59466e for multisig {user_address}',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_SAFE_MULTISIG,
            address=user_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x28eD70032Adc7575d45A0869CfDcCEcdE88C1a74']])
def test_vesting_escrow_grant(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test that the recipient of a newly deployed vesting escrow gets a grant event"""
    tx_hash = deserialize_evm_tx_hash('0x4a95c820e82f7677a33298c1ecba4079e8a94ce8ad2f260e8fba5708dd1cdf83')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=100,
            timestamp=TimestampMS(1730212319000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GRANT,
            asset=Asset('eip155:1/erc20:0x028eC7330ff87667b6dfb0D94b954c820195336c'),
            amount=FVal(grant_amount := '60744.726493694530905846'),
            location_label=ethereum_accounts[0],
            notes=f'Receive a grant of {grant_amount} yvDAI-1 in a Yearn vesting escrow vesting until 30/11/2024 00:00:00',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x9b1B5ddE32cDE7a53D1c70A9f30130547424d781'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x74fEa3FB0eD030e9228026E7F413D66186d3D107']])
def test_vesting_escrow_clawback(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    """Test that the recipient of a revoked vesting escrow gets a clawback loss event"""
    tx_hash = deserialize_evm_tx_hash('0xf3d7b596a889aa93f4f0b06ea5875a9022441a7b6de9a3e211ee865fdfd19aee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=153,
            timestamp=TimestampMS(1746294215000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.CLAWBACK,
            asset=Asset('eip155:1/erc20:0xDe30da39c46104798bB5aA3fe8B9e0e1F348163F'),
            amount=FVal(clawed_amount := '1128350.753900304414003045'),
            location_label=ethereum_accounts[0],
            notes=f'Lose {clawed_amount} GTC unvested from a revoked Yearn vesting escrow',
            tx_ref=tx_hash,
            counterparty=CPT_YEARN_VESTING,
            address=string_to_evm_address('0x7DAE0a882bd4511fa6918e6A35B21aD31a89E3Ab'),
        ),
    ]
