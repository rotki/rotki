from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.privacy_pools.constants import (
    CPT_PRIVACY_POOLS,
    ENTRYPOINT_DEPOSITED_TOPIC,
    PRIVACY_POOLS_DEPLOYMENTS,
    RAGEQUIT_TOPIC,
    V2_ENTRYPOINT,
    V2_POOL_VAULT,
    V2_RELAY,
    WITHDRAWAL_RELAYED_TOPIC,
)
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ARBITRUM_ONE, LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmTransaction,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import address_to_bytes32

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress

DEPLOYMENT = PRIVACY_POOLS_DEPLOYMENTS[ChainID.ETHEREUM]
ARBITRUM_DEPLOYMENT = PRIVACY_POOLS_DEPLOYMENTS[ChainID.ARBITRUM_ONE]
assert DEPLOYMENT.entrypoint is not None
assert DEPLOYMENT.native_pool is not None
assert ARBITRUM_DEPLOYMENT.entrypoint is not None
A_ARB_USDC = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
A_PP_USDC = Asset('eip155:1/erc20:0xC246aFb23482fF9596E9cee5f1f678eFe0EB1ad6')
A_PP_ETH = Asset('eip155:1/erc20:0x66051920D25af4E3596A8a46309F4D045F9D83B7')
V2_PP_USDC_ROUTER = string_to_evm_address('0xe76E793d776c1e207aD7a7fa7C57d27420d85110')
V2_PP_ETH_ROUTER = string_to_evm_address('0x77613D670BB9fD48A9898D0eac8ebf21B566F960')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF26548644BDcFA194128d6bB6761A3eD3FEAF90d']])
def test_privacy_pools_eth_deposit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x90fba70f567b88886808dac6e4453ff72abda6a2f62a1f522475e1600baa2feb')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1755078911000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0011032642639466'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ETH,
            amount=FVal(deposit_amount := '1.5'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} ETH in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=319,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount := '0.007537688442211055'),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as a Privacy Pools deposit fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD45afAA22975bb5200C758151412df92942973F8']])
def test_privacy_pools_eth_withdrawal(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x6b2cfa3d905a226149a529406a618c53b7880496b3b229bc6c54bb073f5a3108')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1755000467000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH,
            amount=FVal(withdrawn_amount := '0.47'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Withdraw {withdrawn_amount} ETH from Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=696,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount := '0.000846'),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as a Privacy Pools withdrawal fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xBffAB3eD459AD6512bF49585C055D7dc688F6177']])
def test_privacy_pools_eth_ragequit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xddceb5ecd4cb3567789c25fa9aa47b31e89f372d1daa58f63c0b0e8d807aad50')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1754994563000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000772785630230592'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH,
            amount=FVal(amount := '0.1'),
            location_label=user_address,
            notes=f'Withdraw {amount} ETH from Privacy Pools via ragequit',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.native_pool,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb941c7aAd899B5F7a575A566C85f5132C8A9E4aa']])
def test_privacy_pools_erc20_deposit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe5934c5295449e91f7d53e981dc9c3c45ce2353e1df2a50080587f3d59cb313b')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1795005635000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001354072566181798'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.TRANSACTION_TO_SELF,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('0'),
            location_label=user_address,
            notes='Transaction to self of 0 ETH',
            address=user_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=139,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_USDC,
            amount=FVal('1000.471216'),
            location_label=user_address,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=140,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_USDC,
            amount=FVal(deposit_amount := '995.46886'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=145,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDC,
            amount=FVal(fee_amount := '5.002356'),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a Privacy Pools deposit fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x40342A90Ff1876bdacf11F99C64ACdf73d29dA68']])
def test_privacy_pools_erc20_withdrawal(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x14d756197f77599c3987f2c39d0ddc628f2329c784da8e7ce9f3f61410a6d9f6')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=688,
            timestamp=(timestamp := TimestampMS(1794970295000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_USDC,
            amount=FVal(withdrawn_amount := '50000'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Withdraw {withdrawn_amount} USDC from Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=691,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDC,
            amount=FVal(fee_amount := '50'),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a Privacy Pools withdrawal fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0c07a6E7F4f9B0084078AE855270965843E694C8']])
def test_privacy_pools_erc20_ragequit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x7531673e809ac696ec98f20787f56c58a36788e8ac610a3cc0f41c4f1a44723b')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1781162507000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00007978588995582'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=77,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_DAI,
            amount=FVal(amount := '4999.95'),
            location_label=user_address,
            notes=f'Withdraw {amount} DAI from Privacy Pools via ragequit',
            counterparty=CPT_PRIVACY_POOLS,
            address=string_to_evm_address('0x1c31C03B8CB2EE674D0F11De77135536db828257'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3c6dDd7d31b4e9696408f6d4Dc852d9dCf442893']])
def test_privacy_pools_arbitrum_one_deposit(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x9bc89b9b39a222e3b0b6b394b0a529ee93366d8fd1a29f8aa6d2b57d0c5b545e')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794240798000)),
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000007400029196'),
            location_label=(user_address := arbitrum_one_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ARB_USDC,
            amount=FVal(deposit_amount := '20'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=ARBITRUM_DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ARB_USDC,
            amount=FVal(fee_amount := '0.100502'),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a Privacy Pools deposit fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=ARBITRUM_DEPLOYMENT.entrypoint,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [['0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045']])
def test_privacy_pools_unlisted_pool_and_missing_internal_tx_fallbacks(
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_transaction_decoder: EthereumTransactionDecoder,
) -> None:
    assert DEPLOYMENT.entrypoint is not None
    assert DEPLOYMENT.native_pool is not None
    user_address = ethereum_accounts[0]
    unlisted_pool = string_to_evm_address('0x1111111111111111111111111111111111111111')
    relayer = string_to_evm_address('0x2222222222222222222222222222222222222222')
    usdc_address = A_USDC.resolve_to_evm_token().evm_address
    gross_raw = 1005_000_000
    net_raw = 1000_000_000

    deposit_tx = EvmTransaction(
        tx_hash=(deposit_hash := deserialize_evm_tx_hash('0x' + '11' * 32)),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1755000000),
        block_number=23000000,
        from_address=user_address,
        to_address=DEPLOYMENT.entrypoint,
        value=0,
        gas=100000,
        gas_price=1,
        gas_used=0,
        input_data=b'',
        nonce=1,
        db_id=1,
    )
    deposit_receipt = EvmTxReceipt(
        tx_hash=deposit_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=2,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=gross_raw.to_bytes(32),
                address=usdc_address,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(user_address),
                    address_to_bytes32(DEPLOYMENT.entrypoint),
                ],
            ),
            EvmTxReceiptLog(
                log_index=1,
                data=net_raw.to_bytes(32),
                address=usdc_address,
                topics=[
                    ERC20_OR_ERC721_TRANSFER,
                    address_to_bytes32(DEPLOYMENT.entrypoint),
                    address_to_bytes32(unlisted_pool),
                ],
            ),
            EvmTxReceiptLog(
                log_index=2,
                data=(1).to_bytes(32) + net_raw.to_bytes(32),
                address=DEPLOYMENT.entrypoint,
                topics=[
                    ENTRYPOINT_DEPOSITED_TOPIC,
                    address_to_bytes32(user_address),
                    address_to_bytes32(unlisted_pool),
                ],
            ),
        ],
    )
    deposit_events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=deposit_tx,
        tx_receipt=deposit_receipt,
        write_buffer=[],
    )
    assert deposit_events == [
        EvmEvent(
            tx_ref=deposit_hash,
            sequence_index=0,
            timestamp=TimestampMS(1755000000000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=deposit_hash,
            sequence_index=1,
            timestamp=TimestampMS(1755000000000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_USDC,
            amount=FVal('1000'),
            location_label=user_address,
            notes='Deposit 1000 USDC in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=deposit_hash,
            sequence_index=4,
            timestamp=TimestampMS(1755000000000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDC,
            amount=FVal('5'),
            location_label=user_address,
            notes='Spend 5 USDC as a Privacy Pools deposit fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ),
    ]

    withdraw_tx = EvmTransaction(
        tx_hash=(withdraw_hash := deserialize_evm_tx_hash('0x' + '22' * 32)),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1755000100),
        block_number=23000001,
        from_address=relayer,
        to_address=DEPLOYMENT.entrypoint,
        value=0,
        gas=100000,
        gas_price=1,
        gas_used=0,
        input_data=b'',
        nonce=1,
        db_id=1,
    )
    withdraw_receipt = EvmTxReceipt(
        tx_hash=withdraw_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=2,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=(500_000_000_000_000_000).to_bytes(32) + (1_000_000_000_000_000).to_bytes(32),
                address=DEPLOYMENT.entrypoint,
                topics=[
                    WITHDRAWAL_RELAYED_TOPIC,
                    address_to_bytes32(relayer),
                    address_to_bytes32(user_address),
                    address_to_bytes32(string_to_evm_address('0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE')),
                ],
            ),
        ],
    )
    withdraw_events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=withdraw_tx,
        tx_receipt=withdraw_receipt,
        write_buffer=[],
    )
    assert withdraw_events == [
        EvmEvent(
            tx_ref=withdraw_hash,
            sequence_index=0,
            timestamp=TimestampMS(1755000100000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH,
            amount=FVal('0.5'),
            location_label=user_address,
            notes='Withdraw 0.5 ETH from Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ), EvmEvent(
            tx_ref=withdraw_hash,
            sequence_index=1,
            timestamp=TimestampMS(1755000100000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001'),
            location_label=user_address,
            notes='Spend 0.001 ETH as a Privacy Pools withdrawal fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.entrypoint,
        ),
    ]

    ragequit_tx = EvmTransaction(
        tx_hash=(ragequit_hash := deserialize_evm_tx_hash('0x' + '33' * 32)),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1755000200),
        block_number=23000002,
        from_address=user_address,
        to_address=DEPLOYMENT.native_pool,
        value=0,
        gas=100000,
        gas_price=1,
        gas_used=0,
        input_data=b'',
        nonce=2,
        db_id=3,
    )
    ragequit_receipt = EvmTxReceipt(
        tx_hash=ragequit_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=2,
        logs=[
            EvmTxReceiptLog(
                log_index=0,
                data=(1).to_bytes(32) + (2).to_bytes(32) + (100_000_000_000_000_000).to_bytes(32),
                address=DEPLOYMENT.native_pool,
                topics=[
                    RAGEQUIT_TOPIC,
                    address_to_bytes32(user_address),
                ],
            ),
        ],
    )
    ragequit_events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=ragequit_tx,
        tx_receipt=ragequit_receipt,
        write_buffer=[],
    )
    assert ragequit_events == [
        EvmEvent(
            tx_ref=ragequit_hash,
            sequence_index=0,
            timestamp=TimestampMS(1755000200000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=ragequit_hash,
            sequence_index=1,
            timestamp=TimestampMS(1755000200000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH,
            amount=FVal('0.1'),
            location_label=user_address,
            notes='Withdraw 0.1 ETH from Privacy Pools via ragequit',
            counterparty=CPT_PRIVACY_POOLS,
            address=DEPLOYMENT.native_pool,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3572BC41eBd79D6Aa3837487F0178c8d34Ddd7a1']])
def test_privacy_pools_v2_eth_deposit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x48ba0be09f4d0d89216eb6d30817d35c1d211c0d7263a611637fb28803cef6fe')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1793932991000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00005461985069715'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ETH,
            amount=FVal(deposit_amount := '0.004'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} ETH in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_ENTRYPOINT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xEb844be80fA1aFD81Ad7336FAEDb5b59325e2A2b']])
def test_privacy_pools_v2_router_erc20_deposit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf5aa1499dd07763e05a8707e49cb72e82f51ca724a90a28b40b8387590619c18')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1795007879000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000186506052788966'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=545,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_USDC,
            amount=FVal(deposit_amount := '50000.005758'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_PP_USDC_ROUTER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xBE2e535eeFB5381B51b0430374E95E3474F88799']])
def test_privacy_pools_v2_router_erc20_withdrawal(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x65147e3b02a065c9d2ec1680262aabd5ce32333aca6362665760b0cb82cb8a7c')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=257,
            timestamp=(timestamp := TimestampMS(1795003511000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_USDC,
            amount=FVal(withdrawn_amount := '40.20401'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Withdraw {withdrawn_amount} USDC from Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_PP_USDC_ROUTER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=272,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_USDC,
            amount=FVal(fee_amount := '0.20398'),
            location_label=user_address,
            notes=f'Spend {fee_amount} USDC as a Privacy Pools withdrawal fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_PP_USDC_ROUTER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xEb844be80fA1aFD81Ad7336FAEDb5b59325e2A2b']])
def test_privacy_pools_v2_router_eth_deposit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe53e0f2c237257629403cce951da8ab82a29477031c1328f82dce2c3d85216ba')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1795008455000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00016480205277527'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ETH,
            amount=FVal(deposit_amount := '2.400000031323364087'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} ETH in Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_PP_ETH_ROUTER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x51892E63f59Fe46f9857813311EFAfac67Db61E1']])
def test_privacy_pools_v2_router_eth_withdrawal(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x04667dfc608ed2044651bfc68d5abb96ef49a5e980fcbfd4a80d582e6eac5030')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1795008323000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH,
            amount=FVal(withdrawn_amount := '0.002168329132191268'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Withdraw {withdrawn_amount} ETH from Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_PP_ETH_ROUTER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=500,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount := '0.000168329079985662'),
            location_label=user_address,
            notes=f'Spend {fee_amount} ETH as a Privacy Pools withdrawal fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_PP_ETH_ROUTER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x30F8E7148374c88BbA25368A6f09d0aF05DC9e26']])
def test_privacy_pools_v2_relay_withdrawal(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x0dc8b353c9b26323eab089d3fd381fd611e3db24adaa9953349160778c7b108d')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1795000475000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('0.0000581756544'),
            location_label=(user_address := ethereum_accounts[0]),
            notes='Receive 0.0000581756544 ETH from 0x01a8Fa4dbb60187aD8d3c3d08E7Fb8C14198A461',
            address=V2_RELAY,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=701,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_PP_USDC,
            amount=FVal(withdrawn_amount := '0.430004248978228899'),
            location_label=user_address,
            notes=f'Withdraw {withdrawn_amount} ppUSDC from Privacy Pools',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_RELAY,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=704,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_PP_USDC,
            amount=FVal(fee_amount := '0.299962641424335382'),
            location_label=user_address,
            notes=f'Spend {fee_amount} ppUSDC as a Privacy Pools withdrawal fee',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_RELAY,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x662464B835C89D5Db4C27eb0cfEC82C8D6Ebb3E8']])
def test_privacy_pools_v2_ragequit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xa2a2a599800439fada4e78579b7693201d1a56f050d740c36257b5c413ea7c02')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794866447000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000083820993191532'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=687,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_PP_ETH,
            amount=FVal(amount := '0.008487900234551298'),
            location_label=user_address,
            notes=f'Withdraw {amount} ppETH from Privacy Pools via ragequit',
            counterparty=CPT_PRIVACY_POOLS,
            address=V2_POOL_VAULT,
        ),
    ]
