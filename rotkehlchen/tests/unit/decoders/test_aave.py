from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.aave.constants import CPT_AAVE_V1, CPT_AAVE_V2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_REN, A_WETH
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.aave import A_ADAI_V1, A_AETH_V1
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
ADDY2 = '0x5727c0481b90a129554395937612d8b9301D6c7b'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_aave_deposit_v1(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410
    """
    tx_hash = deserialize_evm_tx_hash('0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410')  # noqa: E501
    timestamp = TimestampMS(1595376667000)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    amount = '2507.675873220870275072'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00825148723006')),
            location_label=ADDY,
            notes='Burned 0.00825148723006 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=93,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ADAI_V1,
            balance=Balance(amount=FVal('17.91499070977557364')),
            location_label=ADDY,
            notes='Gain 17.91499070977557364 aDAI from aave-v1 as interest',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=94,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal(amount)),
            location_label=ADDY,
            notes=f'Deposit {amount} DAI to aave-v1 from {ADDY}',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x3dfd23A6c5E8BbcFc9581d2E864a68feb6a076d3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=96,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_ADAI_V1,
            balance=Balance(amount=FVal(amount)),
            location_label=ADDY,
            notes=f'Receive {amount} aDAI from aave-v1 for {ADDY}',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_aave_withdraw_v1(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486
    """
    tx_hash = deserialize_evm_tx_hash('0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486')  # noqa: E501
    timestamp = TimestampMS(1598217272000)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    amount = '7968.408929477087756071'
    interest = '88.663672238882760399'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.028562839354')),
            location_label=ADDY,
            notes='Burned 0.028562839354 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=98,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ADAI_V1,
            balance=Balance(amount=FVal(interest)),
            location_label=ADDY,
            notes=f'Gain {interest} aDAI from aave-v1 as interest',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=99,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_ADAI_V1,
            balance=Balance(amount=FVal(amount)),
            location_label=ADDY,
            notes=f'Return {amount} aDAI to aave-v1',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=102,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_DAI,
            balance=Balance(amount=FVal(amount)),
            location_label=ADDY,
            notes=f'Withdraw {amount} DAI from aave-v1',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x3dfd23A6c5E8BbcFc9581d2E864a68feb6a076d3'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY2]])
def test_aave_eth_withdraw_v1(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0xbd333bdd5784c10630aac5683e63f703e660a78d06f95b2ff2a8788a8dade787
    """
    tx_hash = deserialize_evm_tx_hash('0xbd333bdd5784c10630aac5683e63f703e660a78d06f95b2ff2a8788a8dade787')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    amount = '1.000240847792940067'
    interest = '0.000240847792940067'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1605789951000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.021740928')),
            location_label=ADDY2,
            notes='Burned 0.021740928 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=1605789951000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_AETH_V1,
            balance=Balance(amount=FVal(amount)),
            location_label=ADDY2,
            notes=f'Return {amount} aETH to aave-v1',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=1605789951000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal(amount)),
            location_label=ADDY2,
            notes=f'Withdraw {amount} ETH from aave-v1',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x3dfd23A6c5E8BbcFc9581d2E864a68feb6a076d3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=135,
            timestamp=1605789951000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_AETH_V1,
            balance=Balance(amount=FVal(interest)),
            location_label=ADDY2,
            notes=f'Gain {interest} aETH from aave-v1 as interest',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ),
    ]
    assert expected_events == events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x2715273613632226985186221669179813245119')]])  # noqa: E501
def test_aave_v2_enable_collateral(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0xc97b35f42c64a69c01d0e0e4106a655e385c8fa21c812c59a6172199e99cdb7e
    """
    tx_hex = '0xc97b35f42c64a69c01d0e0e4106a655e385c8fa21c812c59a6172199e99cdb7e'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x2715273613632226985186221669179813245119')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=251,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=252,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WETH,
            balance=Balance(),
            location_label=user_address,
            notes='Enable WETH as collateral on AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x2715273613632226985186221669179813245119')]])  # noqa: E501
def test_aave_v2_disable_collateral(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x8fe440f37fd0fa1467067a195ea862db1f96c40634ea7bb3782cc3c3431e9b5c
    """
    tx_hex = '0x8fe440f37fd0fa1467067a195ea862db1f96c40634ea7bb3782cc3c3431e9b5c'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x2715273613632226985186221669179813245119')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=24,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=25,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WETH,
            balance=Balance(),
            location_label=user_address,
            notes='Disable WETH as collateral on AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x2715273613632226985186221669179813245119')]])  # noqa: E501
def test_aave_v2_deposit(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0xf79939503543d76942e076a117ee8467565925f8c6efef973a8e2a6baed4616a
    """
    tx_hex = '0xf79939503543d76942e076a117ee8467565925f8c6efef973a8e2a6baed4616a'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x2715273613632226985186221669179813245119')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=418,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000005150ae84a8cdf00000'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000030ba81f1c18d280636f32af80b9aad02cf0854e'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=419,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000005150ae84a8cdf00000'),  # noqa: E501
                address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=421,
                data=hexstring_to_bytes('0x000000000000000000000000271527361363222698518622166917981324511900000000000000000000000000000000000000000000005150ae84a8cdf00000'),  # noqa: E501
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=419,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal(1500)),
            location_label=user_address,
            notes='Deposit 1500 WETH into AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=420,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),  # aWETH
            balance=Balance(amount=FVal(1500)),
            location_label=user_address,
            notes='Receive 1500 aWETH from AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[
    string_to_evm_address('0x2715273613632226985186221669179813245119'),
    string_to_evm_address('0x6B44ba0a126a2A1a8aa6cD1AdeeD002e141Bcd44'),
]])
def test_aave_v2_withdraw(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x8fe440f37fd0fa1467067a195ea862db1f96c40634ea7bb3782cc3c3431e9b5c
    """
    tx_hex = '0x8fe440f37fd0fa1467067a195ea862db1f96c40634ea7bb3782cc3c3431e9b5c'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x2715273613632226985186221669179813245119')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=25,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000012a66d9c49e79440554'),  # noqa: E501
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000030ba81f1c18d280636f32af80b9aad02cf0854e'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000006b44ba0a126a2a1a8aa6cd1adeed002e141bcd44'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=26,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000012a66d9c49e79440554'),  # noqa: E501
                address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=28,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000012a66d9c49e79440554'),  # noqa: E501
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000006b44ba0a126a2a1a8aa6cd1adeed002e141bcd44'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=26,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            balance=Balance(amount=FVal('5504.540904812179621204')),
            location_label=user_address,
            notes='Withdraw 5504.540904812179621204 WETH from AAVE v2 to 0x6B44ba0a126a2A1a8aa6cD1AdeeD002e141Bcd44',  # noqa: E501
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=27,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
            balance=Balance(amount=FVal('5504.540904812179621204')),
            location_label=user_address,
            notes='Return 5504.540904812179621204 aWETH to AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x00000000000Cd56832cE5dfBcBFf02e7eC639BC9')]])  # noqa: E501
def test_aave_v2_borrow(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x6c8af2a4157632e33fac9d94a03619f54d318ce1254998aabc5384053eb98ffb
    """
    tx_hex = '0x6c8af2a4157632e33fac9d94a03619f54d318ce1254998aabc5384053eb98ffb'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x00000000000Cd56832cE5dfBcBFf02e7eC639BC9')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=306,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000152d02c7e14af6800000'),  # noqa: E501
                address=string_to_evm_address('0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=309,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000152d02c7e14af6800000'),  # noqa: E501
                address=string_to_evm_address('0x408e41876cCCDC0F92210600ef50372656052a38'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000cc12abe4ff81c9378d670de1b57f8e0dd228d77a'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=310,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc900000000000000000000000000000000000000000000152d02c7e14af6800000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000006a3261aa7fbb91a3ce43e'),  # noqa: E501
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000408e41876cccdc0f92210600ef50372656052a38'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=307,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
            balance=Balance(amount=FVal(100000)),
            location_label=user_address,
            notes='Receive 100000 variableDebtREN from AAVE v2',
            counterparty=CPT_AAVE_V2,
            extra_data=None,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=310,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_REN,
            balance=Balance(amount=FVal(100000)),
            location_label=user_address,
            notes='Borrow 100000 REN from AAVE v2 with variable APY 0.80%',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0xCC12AbE4ff81c9378D670De1b57F8e0Dd228D77a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[string_to_evm_address('0x00000000000Cd56832cE5dfBcBFf02e7eC639BC9')]])  # noqa: E501
def test_aave_v2_repay(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x2d43c327482127821603555b00e9feb67e8de1c412a57f55e0fc8ae6bbb32d11
    """
    tx_hex = '0x2d43c327482127821603555b00e9feb67e8de1c412a57f55e0fc8ae6bbb32d11'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = string_to_evm_address('0x00000000000Cd56832cE5dfBcBFf02e7eC639BC9')
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=0,
        block_number=0,
        from_address=user_address,
        to_address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        value=0,
        gas=0,
        gas_price=0,
        gas_used=0,
        input_data=b'',
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=152,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000010f13944fcc61b82177'),  # noqa: E501
                address=string_to_evm_address('0x267EB8Cf715455517F9BD5834AeAE3CeA1EBdbD8'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=155,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000010f13944fcc61b82177'),  # noqa: E501
                address=string_to_evm_address('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000035f6b052c598d933d69a4eec4d04c73a191fe6c2'),  # noqa: E501
                ],
            ), EvmTxReceiptLog(
                log_index=156,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000010f13944fcc61b82177'),  # noqa: E501
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000c011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),  # noqa: E501
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=user_address,
            notes='Burned 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=153,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x267EB8Cf715455517F9BD5834AeAE3CeA1EBdbD8'),
            balance=Balance(amount=FVal('5000.478484297793675639')),
            location_label=user_address,
            notes='Return 5000.478484297793675639 variableDebtSNX to AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=156,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
            balance=Balance(amount=FVal('5000.478484297793675639')),
            location_label=user_address,
            notes='Repay 5000.478484297793675639 SNX on AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x35f6B052C598d933D69A4EEC4D04c73A191fE6c2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x1dB64086b4cdA94884E4FC296799a512dfc564CA']])
def test_aave_v2_liquidation(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Data taken from
    https://etherscan.io/tx/0x2077a54ecae4a06c553f96c120acc0237887fdd1fc2596aab103f6681712974d
    """
    tx_hash = deserialize_evm_tx_hash('0x2077a54ecae4a06c553f96c120acc0237887fdd1fc2596aab103f6681712974d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1684738775000)
    user_address = ethereum_accounts[0]
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0xF63B34710400CAd3e044cFfDcAb00a0f32E33eCf'),
            balance=Balance(amount=FVal('0.910875161581518408')),
            location_label=user_address,
            notes='Payback 0.910875161581518408 variableDebtWETH for an aave-v2 position',
            counterparty=CPT_AAVE_V2,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
            extra_data={'is_liquidation': True},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
            balance=Balance(amount=FVal('0.956418919660594328')),
            location_label=user_address,
            notes='An aave-v2 position got liquidated for 0.956418919660594328 aWETH',
            counterparty=CPT_AAVE_V2,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x8ca7ED9b02ec1E8bEee868a32495Ed5b157eeE08']])
def test_aave_v1_liquidation(
        database: 'DBHandler',
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Data taken from
    https://etherscan.io/tx/0x75ef28b5593efd3f0f9eff338e234f59b2bd34a7148a90ce020122900722a832
    """
    tx_hash = deserialize_evm_tx_hash('0x75ef28b5593efd3f0f9eff338e234f59b2bd34a7148a90ce020122900722a832')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1659244817000)
    user_address = ethereum_accounts[0]
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=187,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=EvmToken('eip155:1/erc20:0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84'),
            balance=Balance(amount=FVal('0.00000020378277191')),
            location_label=user_address,
            notes='Interest payment of 0.00000020378277191 aLINK for aave-v1 position',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x398eC7346DcD622eDc5ae82352F02bE94C62d119'),
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=188,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84'),
            balance=Balance(amount=FVal('38.160293005291481434')),
            location_label=user_address,
            notes='Payback 38.160293005291481434 aLINK for an aave-v1 position',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x398eC7346DcD622eDc5ae82352F02bE94C62d119'),
            extra_data={'is_liquidation': True},
        ),
    ]
    assert expected_events == events
