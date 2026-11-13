from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.lido.constants import WITHDRAWAL_QUEUE
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    CPT_LIDO_CSM,
    LIDO_CSM_MODULE_CONTRACTS,
    LidoCsmStakingModule,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

CSM: Final = LIDO_CSM_MODULE_CONTRACTS[LidoCsmStakingModule.CSM]
CSM_0X02: Final = LIDO_CSM_MODULE_CONTRACTS[LidoCsmStakingModule.CSM_0X02]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x37CfFA4094e7D3437E3D897DD7fa58bFf015e0F0']])
def test_create_node_operator_from_safe(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Operator creation, stETH bond and key upload in one Safe transaction. The events go to
    the Safe, which is the manager and reward address, not to the signer that sent it."""
    tx_hash = deserialize_evm_tx_hash('0x6fff83319cff9b55efa66117533af5c3db6c4de6dbe9003970777e23e689a752')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=887,
            timestamp=(timestamp := TimestampMS(1785088151000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('1.50000000000000001'),
            location_label=(safe_address := ethereum_accounts[0]),
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=889,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=safe_address,
            notes=f'Create Lido CSM node operator 609 with manager and reward address {safe_address}',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=892,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('0.000000000000000012'),
            location_label=safe_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=893,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '1.499999999999999998'),
            location_label=safe_address,
            notes=f'Deposit {amount} stETH as bond for Lido CSM node operator 609',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=896,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=safe_address,
            notes='Add 1 validator key to Lido CSM node operator 609',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=902,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x08dc7C00bcbBb2C063cb0bbe7c6D6c2a009484D2',
            notes=f'Successfully executed safe transaction 0xaf3f43c8c340e210c223d054f2a413d124420e48bdf95bb13c3623e61457b4d4 for multisig {safe_address}',  # noqa: E501
            counterparty='safe-multisig',
            address=safe_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0E408140f4Ef8a366D27804219A7939CfD934Ee5']])
def test_create_node_operator_tracked_reward_address(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Operator 601 has a different manager address. Only the reward address is tracked."""
    tx_hash = deserialize_evm_tx_hash('0x7ad6f865b991f994872f1727173e5c507a319979315ccaecf3aa2319cf79cd05')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782742643000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000226850331291984'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=413,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Create Lido CSM node operator 601 with manager address 0x1FA5A60cFD410C130a64100acc09eA71a273D136 and reward address {user_address}',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=415,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('2.40000000000000001'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=416,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('0.000000000000000011'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=417,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '2.399999999999999999'),
            location_label=user_address,
            notes=f'Deposit {amount} stETH as bond for Lido CSM node operator 601',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=420,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Add 1 validator key to Lido CSM node operator 601',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x64B091b347B27e7ccFad1cb16d4461963459f90A']])
def test_create_csm_0x02_node_operator(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Operator 25 of the CSM 0x02 module, created for a tracked manager address by another
    account. Only the creation concerns the manager."""
    tx_hash = deserialize_evm_tx_hash('0x44a500fa37f30aebb0ac4b9ed5a9dd43aba53188fca89f6b07626ebc045b4c0c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=464,
        timestamp=TimestampMS(1794316343000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.CREATE,
        asset=A_ETH,
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Create Lido CSM 0x02 node operator 25 with manager address {ethereum_accounts[0]} and reward address 0x13d62a2f41787ad8B8ef55973Fd8E5b29CA0875E',  # noqa: E501
        counterparty=CPT_LIDO_CSM,
        address=CSM_0X02.module,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x04c0F1e2c25deBbd915eac3a025E6A7c633Ff20d']])
def test_create_node_operator_eth_bond(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The ETH bond is sent to a gate contract, which creates the operator in the module."""
    tx_hash = deserialize_evm_tx_hash('0x47675463cd553636089e0274c392013a42cd2604b212d38490c624e8745e160b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794183875000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000782442601705102'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=26,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Create Lido CSM node operator 640 with manager and reward address {user_address}',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=27,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount := '2.40000000000000001'),
            location_label=user_address,
            notes=f'Submit {amount} ETH to Lido as bond for Lido CSM node operator 640',
            counterparty=CPT_LIDO_CSM,
            address=string_to_evm_address('0xb8cd8F059Ad7a5dB8CAfDe34aAb007317F7156C8'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=28,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_STETH,
            amount=FVal(steth_amount := '2.400000000000000009'),
            location_label=user_address,
            notes=f'Receive {steth_amount} stETH in exchange for the deposited ETH',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(steth_amount),
            location_label=user_address,
            notes=f'Deposit {steth_amount} stETH as bond for Lido CSM node operator 640',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=34,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Add 1 validator key to Lido CSM node operator 640',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0B2471F50A1b2dB1f6715b2557D2cA075d6f8bC9']])
def test_add_keys_with_eth_bond(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """All the keys a transaction uploads are described by a single event."""
    tx_hash = deserialize_evm_tx_hash('0xb21422bba38cbf4c531141f3a796915ac6e071de91fe70c36e042e0c72706f32')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1764717467000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000120127541549228'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount := '32.5'),
            location_label=user_address,
            notes=f'Submit {amount} ETH to Lido as bond for Lido CSM node operator 331',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_STETH,
            amount=FVal(steth_amount := '32.499999999999999999'),
            location_label=user_address,
            notes=f'Receive {steth_amount} stETH in exchange for the deposited ETH',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(steth_amount),
            location_label=user_address,
            notes=f'Deposit {steth_amount} stETH as bond for Lido CSM node operator 331',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=340,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Add 25 validator keys to Lido CSM node operator 331',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x568AE3743E18B0e384DAE527FD0bD3f69cCEc223']])
def test_add_keys_with_steth_bond(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xdbef4dfa008d11d763ccd39d446cd1e067be9f14e3ca63ddfd59f1d8d5a6d3d3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794066095000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000265264122522862'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=819,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('1.30000000000000001'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=820,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('0.000000000000000011'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=821,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '1.299999999999999999'),
            location_label=user_address,
            notes=f'Deposit {amount} stETH as bond for Lido CSM node operator 99',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=824,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Add 1 validator key to Lido CSM node operator 99',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x11bE399af186362Ad1A83C6888c4d144822DD046']])
def test_add_keys_with_wsteth_bond(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xdcc9eb25709c34e98cb47e0c381a6ada8a60a101580f49cd1835a8e5b6b0b7ac')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1793202335000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000057494644040682'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=432,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_WSTETH,
            amount=FVal(amount := '1.024387458956401418'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=434,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_WSTETH,
            amount=ZERO,
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=435,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_WSTETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Return {amount} wstETH to be unwrapped as bond for Lido CSM node operator 621',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=436,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_STETH,
            amount=FVal(steth_amount := '1.277825174088156388'),
            location_label=user_address,
            notes=f'Unwrap {steth_amount} stETH',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=437,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(steth_amount),
            location_label=user_address,
            notes=f'Deposit {steth_amount} stETH as bond for Lido CSM node operator 621',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=441,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Add 1 validator key to Lido CSM node operator 621',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x12c1eF3208de4805Ba4Ac3fEa6A4F132f8D31243']])
def test_claim_steth(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x69b98baded8fc5b11dee742f4ad32c86fe8d13eb13fe37472faa96edebf39427')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1775810555000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000016929601805406'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=548,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '0.000999999999999999'),
            location_label=user_address,
            notes=f'Claim {amount} stETH from the bond of Lido CSM node operator 35',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x983456BD4EA5A881563eeE4455B8982a4347373A']])
def test_claim_wsteth_with_rewards_distribution(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """A Safe claims the rewards of operator 136 as wstETH to the tracked reward address.
    The rewards distributed to the bond in the same transaction go to the claim recipient."""
    tx_hash = deserialize_evm_tx_hash('0x5267499edcc8c970868a97a8d72f1b2d8d8c4986bd9803555529dcb1c3c7e73c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=398,
            timestamp=(timestamp := TimestampMS(1794169655000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_STETH,
            amount=FVal(rewards := '0.101394104135706043'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Distribute {rewards} stETH of rewards to the bond of Lido CSM node operator 136',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.fee_distributor,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=399,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_STETH,
            amount=FVal(steth_amount := '4.265317088036546931'),
            location_label=user_address,
            notes=f'Claim {steth_amount} stETH from the bond of Lido CSM node operator 136',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=400,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_STETH,
            amount=FVal(steth_amount),
            location_label=user_address,
            notes=f'Wrap {steth_amount} stETH in wstETH',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=401,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_WSTETH,
            amount=FVal(amount := '3.415683960738793912'),
            location_label=user_address,
            notes=f'Receive {amount} wstETH after wrapping',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0522632F660F877b338A5870d243463e24176D83']])
def test_claim_by_tracked_safe_to_untracked_address(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Same claim as above with only the Safe that executed it tracked. The claimed wstETH
    goes to an untracked address, so the claim is informational for the Safe."""
    tx_hash = deserialize_evm_tx_hash('0x5267499edcc8c970868a97a8d72f1b2d8d8c4986bd9803555529dcb1c3c7e73c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=398,
            timestamp=(timestamp := TimestampMS(1794169655000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_STETH,
            amount=FVal(rewards := '0.101394104135706043'),
            location_label=(safe_address := ethereum_accounts[0]),
            notes=f'Distribute {rewards} stETH of rewards to the bond of Lido CSM node operator 136',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.fee_distributor,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=403,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WSTETH,
            amount=FVal(amount := '3.415683960738793912'),
            location_label=safe_address,
            notes=f'Claim {amount} wstETH from the bond of Lido CSM node operator 136 to 0x983456BD4EA5A881563eeE4455B8982a4347373A',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=404,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x752Dc6Bd7C3930DcbB3779f896db856253Cb39C1',
            notes=f'Successfully executed safe transaction 0xaac5959c751625d4d7af1e7211df7de2714c9fcb22430181f804578a3a07d4e3 for multisig {safe_address}',  # noqa: E501
            counterparty='safe-multisig',
            address=safe_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x7AfC67828B64021F4Cfcd2F64e14D828c6659d84']])
def test_claim_unsteth(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The claimed stETH becomes a Lido withdrawal request, whose NFT the user receives."""
    tx_hash = deserialize_evm_tx_hash('0xcbe07b6c7c9985955f64fd8016ea3429fa0c758fa706c3b6d1b3e3782bbc2b7b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794154343000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000103107917195283'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '0.003976131968208409'),
            location_label=user_address,
            notes=f'Claim {amount} stETH from the bond of Lido CSM node operator 634 as Lido withdrawal request 141119',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_STETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Request withdrawal of {amount} stETH from Lido',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset(f'eip155:1/erc721:{WITHDRAWAL_QUEUE}/141119'),
            amount=FVal(ONE),
            location_label=user_address,
            notes='Receive Lido withdrawal request 141119',
            counterparty=CPT_LIDO_CSM,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3C465D82530315cceC1CAd1Fd20164E09B8E4d1f']])
def test_reward_address_change(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x5f4680ecf501704054bee892950a79c2d0e4463152e61d2984cc326ad5aac8d4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794223907000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000011979696070782'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1104,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Change the reward address of Lido CSM node operator 0 from 0x50B06A4037A167073A45ab3cC895c52378B08BA8 to {user_address}',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3C465D82530315cceC1CAd1Fd20164E09B8E4d1f']])
def test_manager_address_reset(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The reward address takes over as manager of operator 0."""
    tx_hash = deserialize_evm_tx_hash('0x187e8bb3ee74ab4a878c711a247e29179e76e060ada13e568121fa871b69e7a4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794223979000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000013270558508383'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=844,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Change the manager address of Lido CSM node operator 0 from 0x50B06A4037A167073A45ab3cC895c52378B08BA8 to {user_address}',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9B4064C9d9801f062f377512e61bD19484e7F365']])
def test_manager_address_change_away_from_tracked_address(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The new manager of operator 42 accepted the change, so only the old one is tracked."""
    tx_hash = deserialize_evm_tx_hash('0xce524338caf90ab2824e23451d8574dde6fdf2162ebf1757c879439eb6be45c6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=915,
        timestamp=TimestampMS(1794039779000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.UPDATE,
        asset=A_ETH,
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes=f'Change the manager address of Lido CSM node operator 42 from {ethereum_accounts[0]} to 0x0000027009702679cC8657B41F152d8c0cFD685d',  # noqa: E501
        counterparty=CPT_LIDO_CSM,
        address=CSM.module,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x556fedf2213A31c7Ab9F8bc8Db5B2254261A5B0b']])
def test_create_node_operator_csm_v1(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """CSM v1 emitted NodeOperatorAdded without the extendedManagerPermissions flag."""
    tx_hash = deserialize_evm_tx_hash('0x6baca0922b17e0f2f0c9aa2f7172c7a06c31818bcf90e0d92f712967c6ffd151')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1729872275000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.028088324263520958'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=93,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Create Lido CSM node operator 1 with manager and reward address {user_address}',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=96,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('15.80000000000000001'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=97,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_STETH,
            amount=FVal('0.000000000000000011'),
            location_label=user_address,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=98,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '15.799999999999999999'),
            location_label=user_address,
            notes=f'Deposit {amount} stETH as bond for Lido CSM node operator 1',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=101,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Add 12 validator keys to Lido CSM node operator 1',
            counterparty=CPT_LIDO_CSM,
            address=CSM.module,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x68889e98A947501CAe1f7E2FB4B771F0234575A1']])
def test_claim_unsteth_with_rewards_csm_v1(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """CSM v1 emitted FeeDistributed instead of OperatorFeeDistributed, and claims were sent
    to the module."""
    tx_hash = deserialize_evm_tx_hash('0x9bb3dc66be7ae1cbdbfcceb7290ff15e04785f04eebbdfe5aa5fbdae9679e5a0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1735437395000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00112929680513689'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=190,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_STETH,
            amount=FVal(rewards := '0.051257225019566509'),
            location_label=user_address,
            notes=f'Distribute {rewards} stETH of rewards to the bond of Lido CSM node operator 60',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.fee_distributor,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=191,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_STETH,
            amount=FVal(amount := '0.086239208213521509'),
            location_label=user_address,
            notes=f'Claim {amount} stETH from the bond of Lido CSM node operator 60 as Lido withdrawal request 65767',  # noqa: E501
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=192,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_STETH,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Request withdrawal of {amount} stETH from Lido',
            counterparty=CPT_LIDO_CSM,
            address=CSM.accounting,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=193,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset(f'eip155:1/erc721:{WITHDRAWAL_QUEUE}/65767'),
            amount=FVal(ONE),
            location_label=user_address,
            notes='Receive Lido withdrawal request 65767',
            counterparty=CPT_LIDO_CSM,
            address=ZERO_ADDRESS,
        ),
    ]
