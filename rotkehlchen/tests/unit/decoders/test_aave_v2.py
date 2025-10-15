from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.aave.constants import (
    STK_AAVE_ADDR,
    STKAAVE_IDENTIFIER,
    V3_MIGRATION_HELPER,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aave.constants import (
    CPT_AAVE,
    CPT_AAVE_V1,
    CPT_AAVE_V2,
    CPT_AAVE_V3,
)
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_AETH_V1,
    A_DAI,
    A_ETH,
    A_POLYGON_POS_MATIC,
    A_REN,
    A_WETH,
)
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
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
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer


A_ADAI_V1 = Asset('eip155:1/erc20:0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d')
ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
ADDY2 = '0x5727c0481b90a129554395937612d8b9301D6c7b'


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_aave_deposit_v1(ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410
    """
    tx_hash = deserialize_evm_tx_hash('0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410')  # noqa: E501
    timestamp = TimestampMS(1595376667000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
            amount=FVal('0.00825148723006'),
            location_label=ADDY,
            notes='Burn 0.00825148723006 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=93,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ADAI_V1,
            amount=FVal('17.91499070977557364'),
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
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ADDY,
            notes=f'Deposit {amount} DAI to aave-v1 from {ADDY}',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x3dfd23A6c5E8BbcFc9581d2E864a68feb6a076d3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=95,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_ADAI_V1,
            amount=FVal(amount),
            location_label=ADDY,
            notes=f'Receive {amount} aDAI from aave-v1 for {ADDY}',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_aave_withdraw_v1(ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486
    """
    tx_hash = deserialize_evm_tx_hash('0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486')  # noqa: E501
    timestamp = TimestampMS(1598217272000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
            amount=FVal('0.028562839354'),
            location_label=ADDY,
            notes='Burn 0.028562839354 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_ADAI_V1,
            amount=FVal(amount),
            location_label=ADDY,
            notes=f'Return {amount} aDAI to aave-v1',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ADDY,
            notes=f'Withdraw {amount} DAI from aave-v1',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x3dfd23A6c5E8BbcFc9581d2E864a68feb6a076d3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ADAI_V1,
            amount=FVal(interest),
            location_label=ADDY,
            notes=f'Gain {interest} aDAI from aave-v1 as interest',
            counterparty=CPT_AAVE_V1,
            address=ZERO_ADDRESS,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY2]])
def test_aave_eth_withdraw_v1(ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0xbd333bdd5784c10630aac5683e63f703e660a78d06f95b2ff2a8788a8dade787
    """
    tx_hash = deserialize_evm_tx_hash('0xbd333bdd5784c10630aac5683e63f703e660a78d06f95b2ff2a8788a8dade787')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
            amount=FVal('0.021740928'),
            location_label=ADDY2,
            notes='Burn 0.021740928 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=1605789951000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_AETH_V1,
            amount=FVal(amount),
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
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=ADDY2,
            notes=f'Withdraw {amount} ETH from aave-v1',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x3dfd23A6c5E8BbcFc9581d2E864a68feb6a076d3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=1605789951000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_AETH_V1,
            amount=FVal(interest),
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
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=251,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                topics=[
                    hexstring_to_bytes('0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'),
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Burn 0 ETH for gas',
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
            amount=ZERO,
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
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=24,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                topics=[
                    hexstring_to_bytes('0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'),
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Burn 0 ETH for gas',
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
            amount=ZERO,
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
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=418,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000005150ae84a8cdf00000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),
                    hexstring_to_bytes('0x000000000000000000000000030ba81f1c18d280636f32af80b9aad02cf0854e'),
                ],
            ), EvmTxReceiptLog(
                log_index=419,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000005150ae84a8cdf00000'),
                address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),
                ],
            ), EvmTxReceiptLog(
                log_index=421,
                data=hexstring_to_bytes('0x000000000000000000000000271527361363222698518622166917981324511900000000000000000000000000000000000000000000005150ae84a8cdf00000'),
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                topics=[
                    hexstring_to_bytes('0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'),
                    hexstring_to_bytes('0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
                    hexstring_to_bytes('0x0000000000000000000000002715273613632226985186221669179813245119'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    with dbevmtx.db.user_write() as cursor, patch_decoder_reload_data():
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
        decoder.reload_data(cursor)
    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WETH,
            amount=FVal(1500),
            location_label=user_address,
            notes='Deposit 1500 WETH into AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),  # aWETH
            amount=FVal(1500),
            location_label=user_address,
            notes='Receive 1500 aWETH from AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2715273613632226985186221669179813245119',
    '0x6B44ba0a126a2A1a8aa6cD1AdeeD002e141Bcd44',
]])
def test_aave_v2_withdraw(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8fe440f37fd0fa1467067a195ea862db1f96c40634ea7bb3782cc3c3431e9b5c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, user_address = TimestampMS(1660809759000), '0.0217873', ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=25,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount=ZERO,
            location_label=user_address,
            notes='Disable WETH as collateral on AAVE v2',
            counterparty=CPT_AAVE_V2,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=26,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
            amount=FVal('5504.540904812179621204'),
            location_label=user_address,
            notes='Return 5504.540904812179621204 aWETH to AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=27,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WETH,
            amount=FVal('5504.540904812179621204'),
            location_label=user_address,
            notes='Withdraw 5504.540904812179621204 WETH from AAVE v2 to 0x6B44ba0a126a2A1a8aa6cD1AdeeD002e141Bcd44',  # noqa: E501
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x00000000000Cd56832cE5dfBcBFf02e7eC639BC9']])
def test_aave_v2_borrow(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6c8af2a4157632e33fac9d94a03619f54d318ce1254998aabc5384053eb98ffb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1622302530000)
    gas_amount = '0.014311845'
    user_address = ethereum_accounts[0]
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xcd9D82d33bd737De215cDac57FE2F7f04DF77FE0'),
            amount=FVal(100000),
            location_label=user_address,
            notes='Receive 100000 variableDebtREN from AAVE v2',
            counterparty=CPT_AAVE_V2,
            extra_data=None,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_REN,
            amount=FVal(100000),
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
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=152,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000010f13944fcc61b82177'),
                address=string_to_evm_address('0x267EB8Cf715455517F9BD5834AeAE3CeA1EBdbD8'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=155,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000010f13944fcc61b82177'),
                address=string_to_evm_address('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),
                    hexstring_to_bytes('0x00000000000000000000000035f6b052c598d933d69a4eec4d04c73a191fe6c2'),
                ],
            ), EvmTxReceiptLog(
                log_index=156,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000010f13944fcc61b82177'),
                address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
                topics=[
                    hexstring_to_bytes('0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'),
                    hexstring_to_bytes('0x000000000000000000000000c011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000cd56832ce5dfbcbff02e7ec639bc9'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Burn 0 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x267EB8Cf715455517F9BD5834AeAE3CeA1EBdbD8'),
            amount=FVal('5000.478484297793675639'),
            location_label=user_address,
            notes='Return 5000.478484297793675639 variableDebtSNX to AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=0,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'),
            amount=FVal('5000.478484297793675639'),
            location_label=user_address,
            notes='Repay 5000.478484297793675639 SNX on AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0x35f6B052C598d933D69A4EEC4D04c73A191fE6c2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x1dB64086b4cdA94884E4FC296799a512dfc564CA']])
def test_aave_v2_liquidation(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Data taken from
    https://etherscan.io/tx/0x2077a54ecae4a06c553f96c120acc0237887fdd1fc2596aab103f6681712974d
    """
    tx_hash = deserialize_evm_tx_hash('0x2077a54ecae4a06c553f96c120acc0237887fdd1fc2596aab103f6681712974d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
            amount=FVal('0.910875161581518408'),
            location_label=user_address,
            notes='Payback 0.910875161581518408 variableDebtWETH for an AAVE v2 position',
            counterparty=CPT_AAVE_V2,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
            extra_data={'is_liquidation': True},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.LOSS,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),
            amount=FVal('0.956418919660594328'),
            location_label=user_address,
            notes='An AAVE v2 position got liquidated for 0.956418919660594328 aWETH',
            counterparty=CPT_AAVE_V2,
            address=string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x8ca7ED9b02ec1E8bEee868a32495Ed5b157eeE08']])
def test_aave_v1_liquidation(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Data taken from
    https://etherscan.io/tx/0x75ef28b5593efd3f0f9eff338e234f59b2bd34a7148a90ce020122900722a832
    """
    tx_hash = deserialize_evm_tx_hash('0x75ef28b5593efd3f0f9eff338e234f59b2bd34a7148a90ce020122900722a832')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
            amount=FVal('0.00000020378277191'),
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
            amount=FVal('38.160293005291481434'),
            location_label=user_address,
            notes='Payback 38.160293005291481434 aLINK for an aave-v1 position',
            counterparty=CPT_AAVE_V1,
            address=string_to_evm_address('0x398eC7346DcD622eDc5ae82352F02bE94C62d119'),
            extra_data={'is_liquidation': True},
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xe903fEed7c1098Ba92E4b7092ca77bBc48503d90']])
def test_aave_v2_supply_ether(ethereum_inquirer, ethereum_accounts):
    """
    Test deposit in aave using the eth wrapper contract. Data taken from
    https://etherscan.io/tx/0xefc9040c100829a391a636f02eb96a9361bd0bc2ca5e8e5f97bbc4a1831cdec9
    """
    tx_hash = deserialize_evm_tx_hash('0xefc9040c100829a391a636f02eb96a9361bd0bc2ca5e8e5f97bbc4a1831cdec9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1646516157000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0104361555519052'),
            location_label=ethereum_accounts[0],
            notes='Burn 0.0104361555519052 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=182,
            timestamp=TimestampMS(1646516157000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Enable WETH as collateral on AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0xcc9a0B7c43DC2a5F023Bb9b738E45B0Ef6B06E04'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=183,
            timestamp=TimestampMS(1646516157000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(0.1),
            location_label=ethereum_accounts[0],
            notes='Deposit 0.1 ETH into AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=string_to_evm_address('0xcc9a0B7c43DC2a5F023Bb9b738E45B0Ef6B06E04'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=184,
            timestamp=TimestampMS(1646516157000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x030bA81f1c18d280636F32af80b9AAd02Cf0854e'),  # aWETH
            amount=FVal(0.1),
            location_label=ethereum_accounts[0],
            notes='Receive 0.1 aWETH from AAVE v2',
            counterparty=CPT_AAVE_V2,
            identifier=None,
            extra_data=None,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0x572f60c0b887203324149D9C308574BcF2dfaD82']])
def test_aave_v2_borrow_polygon(polygon_pos_inquirer, polygon_pos_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x2c2777e24bc8a59171e33d54c2a87d846fc23e7f21a32b99d22397e64429b39c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1711437462000)
    borrowed_amount, gas_fees = '5060', '0.033400048613703322'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas_fees),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas_fees} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:137/erc20:0x75c4d1Fb84429023170086f06E682DcbBF537b7d'),
            amount=FVal(borrowed_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Receive {borrowed_amount} variableDebtmDAI from AAVE v2',
            counterparty=CPT_AAVE_V2,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=EvmToken('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),
            amount=FVal(borrowed_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Borrow {borrowed_amount} DAI from AAVE v2 with variable APY 5.27%',
            counterparty=CPT_AAVE_V2,
            address=string_to_evm_address('0x27F8D03b3a2196956ED754baDc28D73be8830A6e'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6A61Ea7832f84C3096c70f042aB88D9a56732D7B']])
def test_aave_stake(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    """Test that the decoder can decode the stake event from Aave"""
    tx_hash = deserialize_evm_tx_hash('0xfaf96358784483a96a61db6aa4ecf4ac87294b841671ca208de6b5d8f83edf17')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, staked, gas_fees, approval_amount = TimestampMS(1716118019000), '5.126267078394001645', '0.000367527', '115792089237316195423570985008687907853269984665640564038985.825837738726184306'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=64,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_AAVE,
            amount=FVal(approval_amount),
            location_label=ethereum_accounts[0],
            notes=f'Set AAVE spending approval of {ethereum_accounts[0]} by {STK_AAVE_ADDR} to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=STK_AAVE_ADDR,
        ), EvmEvent(
            sequence_index=65,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_AAVE,
            amount=FVal(staked),
            location_label=ethereum_accounts[0],
            notes=f'Stake {staked} AAVE',
            tx_hash=tx_hash,
            counterparty=CPT_AAVE,
            address=STK_AAVE_ADDR,
        ), EvmEvent(
            sequence_index=66,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(STKAAVE_IDENTIFIER),
            amount=FVal(staked),
            location_label=ethereum_accounts[0],
            notes=f'Receive {staked} stkAAVE from staking in Aave',
            counterparty=CPT_AAVE,
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xeD62616a7c1DD354801f4E72389299a81493e004']])
def test_aave_stake_behalfof(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    """Test that the decoder can decode the stake event from Aave from 2022
    The implementation of the proxy contract was different back then."""
    tx_hash = deserialize_evm_tx_hash('0x5532a19bdd4aa26656dc5099d80862a5218cbaf7c96f30cae4a8bb0d19803bfc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, staked, gas_fees, approval_amount = TimestampMS(1684566515000), '58.469937', '0.011340746321963024', '115792089237316195423570985008687907853269984665640564039399.114070913129639935'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=123,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_AAVE,
            amount=FVal(approval_amount),
            location_label=ethereum_accounts[0],
            notes=f'Set AAVE spending approval of {ethereum_accounts[0]} by {STK_AAVE_ADDR} to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=STK_AAVE_ADDR,
        ), EvmEvent(
            sequence_index=124,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_AAVE,
            amount=FVal(staked),
            location_label=ethereum_accounts[0],
            notes=f'Stake {staked} AAVE',
            tx_hash=tx_hash,
            counterparty=CPT_AAVE,
            address=STK_AAVE_ADDR,
        ), EvmEvent(
            sequence_index=125,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(STKAAVE_IDENTIFIER),
            amount=FVal(staked),
            location_label=ethereum_accounts[0],
            notes=f'Receive {staked} stkAAVE from staking in Aave',
            counterparty=CPT_AAVE,
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x201B93778C36Aad0510d96c0a3733A6Efa9d0bC5']])
def test_aave_unstake(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    """Test that the decoder can decode the unstake/redeem event from Aave"""
    tx_hash = deserialize_evm_tx_hash('0xaaef5990d08a0f4cb83b0f98b995f734c96ab6dca41bf7de54c3719fe463ce24')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, unstaked, gas_fees = TimestampMS(1716216731000), '2.71357', '0.001456740929488432'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=449,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(STKAAVE_IDENTIFIER),
            amount=FVal(unstaked),
            location_label=ethereum_accounts[0],
            notes=f'Unstake {unstaked} stkAAVE',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_AAVE,
        ), EvmEvent(
            sequence_index=450,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_AAVE,
            amount=FVal(unstaked),
            location_label=ethereum_accounts[0],
            notes=f'Receive {unstaked} AAVE after unstaking from Aave',
            tx_hash=tx_hash,
            address=STK_AAVE_ADDR,
            counterparty=CPT_AAVE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x76d098850ff14b5922774d156a2D3eb842d88B4a']])
def test_aave_unstake_old(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    """Test that the decoder can decode the unstake/redeem event from Aave back in 2022"""
    tx_hash = deserialize_evm_tx_hash('0x4d28e34be9ccc8a64d0fe9bc30982700b042cd0bdbe7c3bc3968107dce6471e3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, unstaked, gas_fees = TimestampMS(1648296289000), '31.703464134297535778', '0.006477313887656742'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=363,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(STKAAVE_IDENTIFIER),
            amount=FVal(unstaked),
            location_label=ethereum_accounts[0],
            notes=f'Unstake {unstaked} stkAAVE',
            tx_hash=tx_hash,
            address=ZERO_ADDRESS,
            counterparty=CPT_AAVE,
        ), EvmEvent(
            sequence_index=368,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_AAVE,
            amount=FVal(unstaked),
            location_label=ethereum_accounts[0],
            notes=f'Receive {unstaked} AAVE after unstaking from Aave',
            tx_hash=tx_hash,
            address=STK_AAVE_ADDR,
            counterparty=CPT_AAVE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9C836687964D89B52Ae80E3e941745Ddd67e5222']])
def test_stake_reward(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    """Test that the decoder can decode aave reward claiming"""
    tx_hash = deserialize_evm_tx_hash('0xc8ed217572a15a81891ad6480a56150d5b2721c9e517564c3e8ead4439cdcb62')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_fees, amount = TimestampMS(1712099315000), '0.002299167729873168', '0.724507060516081735'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=330,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_AAVE,
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Claim {amount} AAVE from staking',
            tx_hash=tx_hash,
            address=STK_AAVE_ADDR,
            counterparty=CPT_AAVE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6Cf9AA65EBaD7028536E353393630e2340ca6049']])
def test_stake_reward_from_incentives(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    """Test that the decoder can decode aave staking reward claiming in the old way ~2022
    which takes it from the aave incentives"""
    tx_hash = deserialize_evm_tx_hash('0x376c51a492f3f309c408b00278fbb77e54adcbb883f9e0fc190c5478fc153bbf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_fees, amount = TimestampMS(1649141661000), '0.03959433', '14.159467670600490614'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=67,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0x4da27a545c0c5B758a6BA100e3a049001de870f5'),
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Claim {amount} stkAAVE from AAVE v2 incentives',
            tx_hash=tx_hash,
            address=string_to_evm_address('0xd784927Ff2f95ba542BfC824c8a8a98F3495f6b5'),
            counterparty=CPT_AAVE_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x9131C96c791A5aAd3dF4F8C85Acc755a8dD487Ed']])
def test_polygon_incentives(polygon_pos_inquirer: 'PolygonPOSInquirer', polygon_pos_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x6ebaa1502335caa7aa9b6589169885d0361e96bab9ed3b1264308a716d6524c3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user, gas_fees, amount = TimestampMS(1677815446000), polygon_pos_accounts[0], '0.010600028218383051', '2.703388364402691276'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas_fees),
            location_label=user,
            notes=f'Burn {gas_fees} POL for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=199,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:137/erc20:0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'),
            amount=FVal(amount),
            location_label=user,
            notes=f'Claim {amount} WMATIC from AAVE v2 incentives',
            tx_hash=tx_hash,
            address=string_to_evm_address('0x357D51124f59836DeD84c8a1730D72B749d8BC23'),
            counterparty=CPT_AAVE_V2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4BF180A73575D4393Cc794f29fb92C3954a36b5A']])
def test_mainnet_aave_v2_migrate_to_v3_(ethereum_inquirer, ethereum_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xa77ea655f8e0fc7227674633ee1da0c52aadd38f825e2dfa8f44d40867ae1745')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    amount_out, amount_in, approval_amount, gas_fees, timestamp, user = '84.521918902842181053', '76.326951198340166536', '115792089237316195423570985008687907853269984665640564039373.062089010287458882', '0.010769376235131354', TimestampMS(1675004267000), ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=user,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=137,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'),  # stETH
            amount=ZERO,
            location_label=user,
            notes='Disable stETH as collateral on AAVE v2',
            counterparty=CPT_AAVE_V2,
            address=V3_MIGRATION_HELPER,
        ), EvmEvent(
            sequence_index=139,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0x1982b2F5814301d4e9a8b0201555376e62F82428'),  # astETH v2  # noqa: E501
            amount=FVal(approval_amount),
            location_label=user,
            notes=f'Set aSTETH spending approval of {user} by {V3_MIGRATION_HELPER} to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=V3_MIGRATION_HELPER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=157,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0'),
            amount=ZERO,
            location_label=user,
            notes='Enable wstETH as collateral on AAVE v3',
            counterparty=CPT_AAVE_V3,
            address=V3_MIGRATION_HELPER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=158,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=EvmToken('eip155:1/erc20:0x1982b2F5814301d4e9a8b0201555376e62F82428'),  # astETH v2  # noqa: E501
            amount=FVal(amount_out),
            location_label=user,
            notes=f'Migrate {amount_out} aSTETH from AAVE v2',
            counterparty=CPT_AAVE_V2,
            address=V3_MIGRATION_HELPER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=159,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x0B925eD163218f6662a35e0f0371Ac234f9E9371'),  # aEthwstETH v3  # noqa: E501
            amount=FVal(amount_in),
            location_label=user,
            notes=f'Receive {amount_in} aEthwstETH from migrating an AAVE v2 position to v3',
            counterparty=CPT_AAVE_V3,
        ),
    ]
    assert events == expected_events
