import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.makerdao.constants import (
    CPT_MAKERDAO_MIGRATION,
    CPT_VAULT,
    MAKERDAO_MIGRATION_ADDRESS,
)
from rotkehlchen.chain.ethereum.modules.makerdao.sai.constants import CPT_SAI
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_SAI, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmInternalTransaction,
    EvmTransaction,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

A_PETH = Asset('eip155:1/erc20:0xf53AD2c6851052A81B42133467480961B2321C09')
ADDY_1 = '0x01349510117dC9081937794939552463F5616dfb'
ADDY_2 = '0xD5684Ae2a4a722B8B31168AcF6fF3477617073ea'
ADDY_3 = '0x277E4b7F5DaB01C8E4389B930d3Bd1c9690CE1E8'
ADDY_4 = '0xB4be361f092D9d5edFE8606fD53260eCED3b776E'
ADDY_5 = '0x8d44EAAe757884f4F8fb4664D07ACECee71CFd89'
ADDY_6 = '0x005e157Ae9708c55dB34e3e936CD3ebEE7265Fbc'
ADDY_7 = '0xb0e83C2D71A991017e0116d58c5765Abc57384af'
ADDY_8 = '0x153685A03c2025b6825AE164e2ff5681EE487667'
ADDY_9 = '0x6D1723Af1727d857964d12f19ed92E63736c8dA2'
ADDY_10 = '0x720972Dc53741a72fEE22400828122836640a74b'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_1]])
def test_makerdao_sai_new_cdp(ethereum_transaction_decoder):
    """
    Data for cdp creation is taken from
    https://etherscan.io/tx/0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0
    """
    tx_hash = deserialize_evm_tx_hash('0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513958719,
        block_number=4777541,
        from_address=ADDY_1,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xfcfff16f'),
        nonce=1021,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=21,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004fcfff16f'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xfcfff16f00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000001349510117dc9081937794939552463f5616dfb'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=22,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000083'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x89b8893b806db50897c8e2362c71571cfaeb9761ee40727f683f1793cda9df16'),
                    hexstring_to_bytes('0x00000000000000000000000001349510117dc9081937794939552463f5616dfb'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    assert len(events) == 2
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1513958719000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.00393701451),
            location_label=ADDY_1,
            notes='Burn 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=23,
            timestamp=1513958719000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ADDY_1,
            notes='Create CDP 131',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_2]])
def test_makerdao_sai_borrow_sai(ethereum_transaction_decoder):
    """
    Data for sai borrow is taken from
    https://etherscan.io/tx/0x4aed2d2fe5712a5b65cb6866c51ae672a53e39fa25f343e4c6ebaa8eae21de80
    """
    tx_hash = deserialize_evm_tx_hash('0x4aed2d2fe5712a5b65cb6866c51ae672a53e39fa25f343e4c6ebaa8eae21de80')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513957014,
        block_number=4777443,
        from_address=ADDY_2,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=940000,
        gas_price=40000000000,
        gas_used=127221,
        input_data=hexstring_to_bytes('0x440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
        nonce=47,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=44,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000076'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),
                ],
            ), EvmTxReceiptLog(
                log_index=45,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000076'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),
                ],
            ), EvmTxReceiptLog(
                log_index=46,
                data=hexstring_to_bytes(
                    '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000076'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),
                ],
            ), EvmTxReceiptLog(
                log_index=47,
                data=hexstring_to_bytes(
                    '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000076'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),
                ],
            ), EvmTxReceiptLog(
                log_index=48,
                data=hexstring_to_bytes(
                    '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000076'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),
                ],
            ), EvmTxReceiptLog(
                log_index=49,
                data=hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                ],
            ), EvmTxReceiptLog(
                log_index=50,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=51,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba000000000000000000000000000000000000000000000000000000000000007600000000000000000000000000000000000000000000003635c9adc5dea00000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000d5684ae2a4a722b8b31168acf6ff3477617073ea'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000076'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000003635c9adc5dea00000'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    assert len(events) == 2
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1513957014000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00508884'),
            location_label=ADDY_2,
            notes='Burn 0.00508884 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=45,
            timestamp=1513957014000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            amount=FVal('1000'),
            location_label=ADDY_2,
            notes='Borrow 1000 SAI from CDP 118',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_3]])
def test_makerdao_sai_close_cdp(ethereum_transaction_decoder):
    """
    Data for cdp closure is taken from
    https://etherscan.io/tx/0xc851e18df6dec02ac2efff000298001e839dde3d6e99d25d1d98ecb0d390c9a6
    """
    tx_hash = deserialize_evm_tx_hash('0xc851e18df6dec02ac2efff000298001e839dde3d6e99d25d1d98ecb0d390c9a6')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513954042,
        block_number=4777277,
        from_address=ADDY_3,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=183231,
        gas_price=40000000000,
        gas_used=92770,
        input_data=hexstring_to_bytes('0xb84d21060000000000000000000000000000000000000000000000000000000000000065'),
        nonce=302,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=32,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024b84d21060000000000000000000000000000000000000000000000000000000000000065'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb84d210600000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000277e4b7f5dab01c8e4389b930d3bd1c9690ce1e8'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000065'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=33,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024b84d21060000000000000000000000000000000000000000000000000000000000000065'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),

                topics=[
                    hexstring_to_bytes('0xb84d210600000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000277e4b7f5dab01c8e4389b930d3bd1c9690ce1e8'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000065'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=34,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024b84d21060000000000000000000000000000000000000000000000000000000000000065'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb84d210600000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000277e4b7f5dab01c8e4389b930d3bd1c9690ce1e8'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000065'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=35,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000977e7eff4a9a225b'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x000000000000000000000000277e4b7f5dab01c8e4389b930d3bd1c9690ce1e8'),
                ],
            ), EvmTxReceiptLog(
                log_index=36,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),

                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=37,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024b84d21060000000000000000000000000000000000000000000000000000000000000065'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),

                topics=[
                    hexstring_to_bytes('0xb84d210600000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000277e4b7f5dab01c8e4389b930d3bd1c9690ce1e8'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000065'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor, patch_decoder_reload_data():
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1513954042000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0037108'),
            location_label=ADDY_3,
            notes='Burn 0.0037108 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=33,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ADDY_3,
            notes='Close CDP 101',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_PETH,
            amount=FVal('10.916302181726036571'),
            location_label=ADDY_3,
            notes='Decrease CDP collateral by 10.916302181726036571 PETH',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_4]])
def test_makerdao_sai_repay_sai(ethereum_transaction_decoder):
    """
    Data for repayment of sai loan is taken from
    https://etherscan.io/tx/0xe964cb12f4bbfa1ba4b6db8464eb3f2d4234ceafb0b5ec5f4a2188b0264bab27
    """
    tx_hash = deserialize_evm_tx_hash('0xe964cb12f4bbfa1ba4b6db8464eb3f2d4234ceafb0b5ec5f4a2188b0264bab27')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513958625,
        block_number=4777277,
        from_address=ADDY_4,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=193606,
        gas_price=40000000000,
        gas_used=128881,
        input_data=hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
        nonce=77,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=20,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=21,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=22,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=23,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=24,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=25,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=26,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b3810100000000000000000000000000000000000000000000000000000000000000670000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000067'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                ],
            ), EvmTxReceiptLog(
                log_index=27,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000056bc75e2d63100000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                ],
            ), EvmTxReceiptLog(
                log_index=28,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000001f118c57e32'),
                address=string_to_evm_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000b4be361f092d9d5edfe8606fd53260eced3b776e'),
                    hexstring_to_bytes('0x00000000000000000000000069076e44a9c70a67d5b79d95795aba299083c275'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    timestamp = TimestampMS(1513958625000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00515524'),
            location_label=ADDY_4,
            notes='Burn 0.00515524 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=21,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset('eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
            amount=FVal('100'),
            location_label=ADDY_4,
            notes='Repay 100 SAI to CDP 103',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=29,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
            amount=FVal('0.000002135014342194'),
            location_label=ADDY_4,
            notes='Send 0.000002135014342194 MKR from 0xB4be361f092D9d5edFE8606fD53260eCED3b776E to 0x69076e44a9C70a67D5b79d95795Aba299083c275',  # noqa: E501
            address=string_to_evm_address('0x69076e44a9C70a67D5b79d95795Aba299083c275'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_5]])
def test_makerdao_sai_deposit_weth(ethereum_transaction_decoder):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0x5a7849ab4b7f7de2b005deddef24a094387c248c3bcb06066109bd7852c1d8af
    """
    tx_hash = deserialize_evm_tx_hash('0x5a7849ab4b7f7de2b005deddef24a094387c248c3bcb06066109bd7852c1d8af')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513955555,
        block_number=4777359,
        from_address=ADDY_5,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=139590,
        gas_price=40000000000,
        gas_used=92590,
        input_data=hexstring_to_bytes('0x049878f3000000000000000000000000000000000000000000000004e1003b28d9280000'),
        nonce=250,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=2,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024049878f3000000000000000000000000000000000000000000000004e1003b28d9280000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x049878f300000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000008d44eaae757884f4f8fb4664d07acecee71cfd89'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000004e1003b28d9280000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=3,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000004e14781c3f76dad52'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000008d44eaae757884f4f8fb4664d07acecee71cfd89'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=4,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000004e1003b28d9280000'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x0000000000000000000000008d44eaae757884f4f8fb4664d07acecee71cfd89'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    timestamp = TimestampMS(1513955555000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0037036'),
            location_label=ADDY_5,
            notes='Burn 0.0037036 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WETH,
            amount=FVal('90.02006235538821461'),
            location_label=ADDY_5,
            notes='Supply 90.02006235538821461 WETH to Sai vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_PETH,
            amount=FVal('90'),
            location_label=ADDY_5,
            notes='Receive 90 PETH from Sai Vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_5]])
def test_makerdao_sai_deposit_peth(ethereum_transaction_decoder):
    """
    Data for deposit is taken from
    https://etherscan.io/tx/0xc8bd1d3556706e659e907b515185ce7e139777229f257e79a6b0b26e2a536e2c
    """
    tx_hash = deserialize_evm_tx_hash('0xc8bd1d3556706e659e907b515185ce7e139777229f257e79a6b0b26e2a536e2c')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513955635,
        block_number=4777359,
        from_address=ADDY_5,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=74253,
        gas_price=40000000000,
        gas_used=34502,
        input_data=hexstring_to_bytes('0xb3b77a510000000000000000000000000000000000000000000000000000000000000003000000000000000000000000000000000000000000000004e1003b28d9280000'),
        nonce=251,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=30,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044b3b77a510000000000000000000000000000000000000000000000000000000000000003000000000000000000000000000000000000000000000004e1003b28d9280000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb3b77a5100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000008d44eaae757884f4f8fb4664d07acecee71cfd89'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000003'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000004e1003b28d9280000'),
                ],
            ), EvmTxReceiptLog(
                log_index=31,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000004e1003b28d9280000'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000008d44eaae757884f4f8fb4664d07acecee71cfd89'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    timestamp = TimestampMS(1513955635000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00138008'),
            location_label=ADDY_5,
            notes='Burn 0.00138008 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=32,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_PETH,
            amount=FVal('90'),
            notes='Increase CDP collateral by 90 PETH',
            location_label=ADDY_5,
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_6]])
def test_makerdao_sai_liquidation(ethereum_transaction_decoder):
    """
    Data for liquidation is taken from
    https://etherscan.io/tx/0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba
    """
    tx_hash = deserialize_evm_tx_hash('0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1513952436,
        block_number=4777359,
        from_address=ADDY_6,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=249556,
        gas_price=40000000000,
        gas_used=119631,
        input_data=hexstring_to_bytes('0x40cc88540000000000000000000000000000000000000000000000000000000000000050'),
        nonce=251,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=23,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002440cc88540000000000000000000000000000000000000000000000000000000000000050'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x40cc885400000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000005e157ae9708c55db34e3e936cd3ebee7265fbc'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000050'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=24,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=25,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002440cc88540000000000000000000000000000000000000000000000000000000000000050'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x40cc885400000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000005e157ae9708c55db34e3e936cd3ebee7265fbc'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000050'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=26,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002440cc88540000000000000000000000000000000000000000000000000000000000000050'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x40cc885400000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000005e157ae9708c55db34e3e936cd3ebee7265fbc'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000050'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=27,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000001158e460913d00000'),
                address=string_to_evm_address('0x79F6D0f646706E1261aCF0b93DCB864f357d4680'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x000000000000000000000000bda109309f9fafa6dd6a9cb9f1df4085b27ee8ef'),
                ],
            ), EvmTxReceiptLog(
                log_index=28,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=29,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000009385260f95e68e'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x000000000000000000000000bda109309f9fafa6dd6a9cb9f1df4085b27ee8ef'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    assert len(events) == 2
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1513952436000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00478524'),
            location_label=ADDY_6,
            notes='Burn 0.00478524 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=24,
            timestamp=1513952436000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.LOSS,
            event_subtype=HistoryEventSubType.LIQUIDATE,
            asset=A_PETH,
            amount=FVal('0.041523220093200014'),
            location_label=ADDY_6,
            notes='Liquidate 0.041523220093200014 PETH for CDP 80',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_7]])
def test_makerdao_sai_collateral_removal(ethereum_transaction_decoder):
    """
    Data for abstracted collateral removal is taken from
    https://etherscan.io/tx/0x8c95ecc864db038a42c6cd9d6cab17e12f1f56332b140d903948a69d8b9e4308
    """
    tx_hash = deserialize_evm_tx_hash('0x8c95ecc864db038a42c6cd9d6cab17e12f1f56332b140d903948a69d8b9e4308')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1514047441,
        block_number=4783564,
        from_address=ADDY_7,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=164502,
        gas_price=32000000000,
        gas_used=110274,
        input_data=hexstring_to_bytes('0xa5cd184e000000000000000000000000000000000000000000000000000000000000004d00000000000000000000000000000000000000000000000029a2241af62c0000'),
        nonce=251,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=31,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044a5cd184e000000000000000000000000000000000000000000000000000000000000004d00000000000000000000000000000000000000000000000029a2241af62c0000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xa5cd184e00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b0e83c2d71a991017e0116d58c5765abc57384af'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000004d'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000029a2241af62c0000'),
                ],
            ), EvmTxReceiptLog(
                log_index=32,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000029a2241af62c0000'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x000000000000000000000000b0e83c2d71a991017e0116d58c5765abc57384af'),
                ],
            ), EvmTxReceiptLog(
                log_index=33,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=34,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044a5cd184e000000000000000000000000000000000000000000000000000000000000004d00000000000000000000000000000000000000000000000029a2241af62c0000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xa5cd184e00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000b0e83c2d71a991017e0116d58c5765abc57384af'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000000000000000004d'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000029a2241af62c0000'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor, patch_decoder_reload_data():
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    timestamp = TimestampMS(1514047441000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003528768'),
            location_label=ADDY_7,
            notes='Burn 0.003528768 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=33,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_PETH,
            amount=FVal(3),
            location_label=ADDY_7,
            notes='Decrease CDP collateral by 3 PETH',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_8]])
def test_makerdao_sai_underlying_collateral_removal(ethereum_transaction_decoder):
    """
    Data for underlying collateral removal is taken from
    https://etherscan.io/tx/0x6467c080d5c0af9756681a368417fb802206d832f51d20b19c08d7c46a4216b0
    """
    tx_hash = deserialize_evm_tx_hash('0x6467c080d5c0af9756681a368417fb802206d832f51d20b19c08d7c46a4216b0')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1663338359,
        block_number=15546757,
        from_address=ADDY_8,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=126261,
        gas_price=13587776368,
        gas_used=78808,
        input_data=hexstring_to_bytes('0x7f8661a100000000000000000000000000000000000000000000000000dbe39c827cfa65'),
        nonce=3460,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=357,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000247f8661a100000000000000000000000000000000000000000000000000dbe39c827cfa65'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x7f8661a100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000153685a03c2025b6825ae164e2ff5681ee487667'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000dbe39c827cfa65'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=358,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000e724e3c30254a2'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x000000000000000000000000153685a03c2025b6825ae164e2ff5681ee487667'),
                ],
            ), EvmTxReceiptLog(
                log_index=359,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000dbe39c827cfa65'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'),
                    hexstring_to_bytes('0x000000000000000000000000153685a03c2025b6825ae164e2ff5681ee487667'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor, patch_decoder_reload_data():
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
        ethereum_transaction_decoder.reload_data(cursor)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    timestamp = TimestampMS(1663338359000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001070825480009344'),
            location_label=ADDY_8,
            notes='Burn 0.001070825480009344 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=359,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH,
            amount=FVal('0.065061280268047522'),
            location_label=ADDY_8,
            notes='Withdraw 0.065061280268047522 WETH from Sai vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [[ADDY_9, ADDY_10]])
def test_makerdao_sai_proxy_interaction(ethereum_transaction_decoder):
    """
    Data for proxy interaction is taken from
    https://etherscan.io/tx/0xf4203a8b507b0b382903bd8d35dcff29aea98de76b89f745d94705d54b67646f
    """
    tx_hash = deserialize_evm_tx_hash('0xf4203a8b507b0b382903bd8d35dcff29aea98de76b89f745d94705d54b67646f')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1565146195,
        block_number=8300924,
        from_address=ADDY_9,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=6000000000000000,
        gas=1453333,
        gas_price=3000000000,
        gas_used=948411,
        input_data=hexstring_to_bytes('0xd3140a650000000000000000000000004678f0a6958e4d2bc4f1baf7bc52e8f3564f3fe4000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af300000000000000000000000000000000000000000000000000d529ae9e860000'),
        nonce=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=55,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B'),
                topics=[
                    hexstring_to_bytes('0xce241d7ca1f669fee44b6fc00b8eba2df3bb514eed0f6f668f8f89096e81ed94'),
                    hexstring_to_bytes('0x000000000000000000000000a26e15c895efc0616177b7c1e7270a4c7d51c997'),
                ],
            ), EvmTxReceiptLog(
                log_index=56,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B'),
                topics=[
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000a26e15c895efc0616177b7c1e7270a4c7d51c997'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=57,
                data=hexstring_to_bytes('0x0000000000000000000000003e4d3c5b1d1de05157b5a46eef2a9282ad22a60b000000000000000000000000271293c67e2d3140a0e9381eff1f9b01e07b0795'),
                address=string_to_evm_address('0xA26e15C895EFc0616177B7c1e7270A4C7D51C997'),
                topics=[
                    hexstring_to_bytes('0x259b30ca39885c6d801a0b5dbc988640f3c25e2f37531fe138c5c5af8955d41b'),
                    hexstring_to_bytes('0x0000000000000000000000004678f0a6958e4d2bc4f1baf7bc52e8f3564f3fe4'),
                    hexstring_to_bytes('0x0000000000000000000000006d1723af1727d857964d12f19ed92e63736c8da2'),
                ],
            ), EvmTxReceiptLog(
                log_index=58,
                data=hexstring_to_bytes('0x'),
                address=string_to_evm_address('0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B'),
                topics=[
                    hexstring_to_bytes('0xce241d7ca1f669fee44b6fc00b8eba2df3bb514eed0f6f668f8f89096e81ed94'),
                    hexstring_to_bytes('0x0000000000000000000000006d1723af1727d857964d12f19ed92e63736c8da2'),
                ],
            ), EvmTxReceiptLog(
                log_index=59,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004fcfff16f'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xfcfff16f00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=60,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x89b8893b806db50897c8e2362c71571cfaeb9761ee40727f683f1793cda9df16'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                ],
            ), EvmTxReceiptLog(
                log_index=61,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000001550f7dca70000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                ],
            ), EvmTxReceiptLog(
                log_index=62,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024049878f300000000000000000000000000000000000000000000000000146f6865eb7248'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x049878f300000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000146f6865eb7248'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=63,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000001550f7dca70000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=64,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000146f6865eb7248'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                ],
            ), EvmTxReceiptLog(
                log_index=65,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044b3b77a5100000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000146f6865eb7248'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb3b77a5100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000146f6865eb7248'),
                ],
            ), EvmTxReceiptLog(
                log_index=66,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000146f6865eb7248'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=67,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba00000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                ],
            ), EvmTxReceiptLog(
                log_index=68,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba00000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                ],
            ), EvmTxReceiptLog(
                log_index=69,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba00000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                ],
            ), EvmTxReceiptLog(
                log_index=70,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba00000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                ],
            ), EvmTxReceiptLog(
                log_index=71,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba00000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                ],
            ), EvmTxReceiptLog(
                log_index=72,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                ],
            ), EvmTxReceiptLog(
                log_index=73,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=74,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba00000000000000000000000000000000000000000000000000000000000103b200000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                ],
            ), EvmTxReceiptLog(
                log_index=75,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000d529ae9e860000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x0000000000000000000000006d1723af1727d857964d12f19ed92e63736c8da2'),
                ],
            ), EvmTxReceiptLog(
                log_index=76,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044baa8529c00000000000000000000000000000000000000000000000000000000000103b20000000000000000000000003e4d3c5b1d1de05157b5a46eef2a9282ad22a60b'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xbaa8529c00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000103b2'),
                    hexstring_to_bytes('0x0000000000000000000000003e4d3c5b1d1de05157b5a46eef2a9282ad22a60b'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    timestamp = TimestampMS(1565146195000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002845233'),
            location_label=ADDY_9,
            notes='Burn 0.002845233 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=59,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ADDY_9,
            notes='Create DSR proxy 0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B with owner 0x6D1723Af1727d857964d12f19ed92E63736c8dA2',  # noqa: E501
            address=string_to_evm_address('0x3e4d3c5B1d1dE05157B5a46Eef2A9282aD22A60B'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=60,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x526af336D614adE5cc252A407062B8861aF998F5',
            notes='Create CDP 66482',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=61,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal('0.006'),
            location_label=ADDY_9,
            notes='Supply 0.006 ETH to Sai vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=66,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_PETH,
            amount=FVal('0.005751993711424072'),
            location_label='0x526af336D614adE5cc252A407062B8861aF998F5',
            notes='Receive 0.005751993711424072 PETH from Sai Vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=77,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            amount=FVal('0.06'),
            location_label=ADDY_9,
            notes='Borrow 0.06 SAI from CDP 66482',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x526af336D614adE5cc252A407062B8861aF998F5'),
            extra_data={'cdp_id': 66482},
        ),
    ]
    assert events == expected_events

    # sai repayment
    # https://etherscan.io/tx/0x96c8d55100427de5edbf33fb41623b42966f7ae7273b55edaf6f7a5178d93594
    tx_hash = deserialize_evm_tx_hash('0x96c8d55100427de5edbf33fb41623b42966f7ae7273b55edaf6f7a5178d93594')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1588030530,
        block_number=8300924,
        from_address=ADDY_10,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=427422,
        gas_price=2000000000,
        gas_used=215905,
        input_data=hexstring_to_bytes('0x1cff79cd000000000000000000000000526af336d614ade5cc252a407062b8861af998f500000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000064a3dc65a7000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af30000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec8000000000000000000000000000000000000000000000000000000000000'),
        nonce=22,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=83,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000e41cff79cd000000000000000000000000526af336d614ade5cc252a407062b8861af998f500000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000064a3dc65a7000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af30000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec8000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
                topics=[
                    hexstring_to_bytes('0x1cff79cd00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000720972dc53741a72fee22400828122836640a74b'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000040'),
                ],
            ), EvmTxReceiptLog(
                log_index=84,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000720972dc53741a72fee22400828122836640a74b'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=85,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000246f78ee0d0000000000000000000000000000000000000000000000000000000000025ee1'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x6f78ee0d00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=86,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000246f78ee0d0000000000000000000000000000000000000000000000000000000000025ee1'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x6f78ee0d00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=87,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000246f78ee0d0000000000000000000000000000000000000000000000000000000000025ee1'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x6f78ee0d00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=88,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=89,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),
                address=string_to_evm_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=90,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=91,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=92,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=93,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=94,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=95,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=96,
                data=hexstring_to_bytes('00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000004473b381010000000000000000000000000000000000000000000000000000000000025ee10000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x73b3810100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                ],
            ), EvmTxReceiptLog(
                log_index=97,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000001bc16d674ec80000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )

    assert len(events) == 2
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1588030530000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00043181'),
            location_label=ADDY_10,
            notes='Burn 0.00043181 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=85,
            timestamp=1588030530000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_SAI,
            amount=FVal(2),
            location_label=ADDY_10,
            notes='Repay 2 SAI to CDP 155361',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
        ),
    ]
    assert events == expected_events

    # proxy interaction
    # https://etherscan.io/tx/0x3c85624d0103f946e02c76bf4f801e72e6a753679601611c13ba2d736db1c004
    tx_hash = deserialize_evm_tx_hash('0x3c85624d0103f946e02c76bf4f801e72e6a753679601611c13ba2d736db1c004')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1588035170,
        block_number=8300924,
        from_address=ADDY_10,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=80000000000000000,
        gas=799894,
        gas_price=2000000000,
        gas_used=468552,
        input_data=hexstring_to_bytes('0x1cff79cd000000000000000000000000526af336d614ade5cc252a407062b8861af998f500000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044516e9aec000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af30000000000000000000000000000000000000000000000004563918244f4000000000000000000000000000000000000000000000000000000000000'),
        nonce=25,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=97,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000011c37937e080000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000c41cff79cd000000000000000000000000526af336d614ade5cc252a407062b8861af998f500000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044516e9aec000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af30000000000000000000000000000000000000000000000004563918244f4000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
                topics=[
                    hexstring_to_bytes('0x1cff79cd00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000720972dc53741a72fee22400828122836640a74b'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000040'),
                ],
            ), EvmTxReceiptLog(
                log_index=98,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004fcfff16f'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xfcfff16f00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=99,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x89b8893b806db50897c8e2362c71571cfaeb9761ee40727f683f1793cda9df16'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=100,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000011c37937e080000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=101,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=102,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024049878f3000000000000000000000000000000000000000000000000010e37c97b8d15f9'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x049878f300000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000010e37c97b8d15f9'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=103,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000011c37937e080000'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=104,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000010e37c97b8d15f9'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=105,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044b3b77a510000000000000000000000000000000000000000000000000000000000025ee2000000000000000000000000000000000000000000000000010e37c97b8d15f9'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb3b77a5100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000010e37c97b8d15f9'),
                ],
            ), EvmTxReceiptLog(
                log_index=106,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000010e37c97b8d15f9'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=107,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba0000000000000000000000000000000000000000000000000000000000025ee20000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                ],
            ), EvmTxReceiptLog(
                log_index=108,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba0000000000000000000000000000000000000000000000000000000000025ee20000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                ],
            ), EvmTxReceiptLog(
                log_index=109,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba0000000000000000000000000000000000000000000000000000000000025ee20000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                ],
            ), EvmTxReceiptLog(
                log_index=110,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba0000000000000000000000000000000000000000000000000000000000025ee20000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                ],
            ), EvmTxReceiptLog(
                log_index=111,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba0000000000000000000000000000000000000000000000000000000000025ee20000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                ],
            ), EvmTxReceiptLog(
                log_index=112,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=113,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=114,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044440f19ba0000000000000000000000000000000000000000000000000000000000025ee20000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x440f19ba00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee2'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                ],
            ), EvmTxReceiptLog(
                log_index=115,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000004563918244f40000'),
                address=string_to_evm_address('0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000720972dc53741a72fee22400828122836640a74b'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert len(events) == 5
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1588035170000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000937104'),
            location_label=ADDY_10,
            notes='Burn 0.000937104 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=1588035170000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x72Ee0f9AB3678148CC0700243CB38577Bd290869',
            notes='Create CDP 155362',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=1588035170000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal('0.08'),
            location_label=ADDY_10,
            notes='Supply 0.08 ETH to Sai vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=106,
            timestamp=1588035170000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_PETH,
            amount=FVal('0.076059582212675065'),
            location_label='0x72Ee0f9AB3678148CC0700243CB38577Bd290869',
            notes='Receive 0.076059582212675065 PETH from Sai Vault',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=117,
            timestamp=1588035170000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            amount=FVal(5),
            location_label=ADDY_10,
            notes='Borrow 5 SAI from CDP 155362',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
            extra_data={'cdp_id': 155362},
        ),
    ]
    assert events == expected_events

    # another proxy interaction
    # https://etherscan.io/tx/0x4e569aa1f23dc771f1c9ad05ab7cdb0af2607358b166a8137b702f81b88e37b9
    tx_hash = deserialize_evm_tx_hash('0x4e569aa1f23dc771f1c9ad05ab7cdb0af2607358b166a8137b702f81b88e37b9')  # noqa: E501
    transaction = EvmTransaction(
        chain_id=ChainID.ETHEREUM,
        tx_hash=tx_hash,
        timestamp=1588030595,
        block_number=9957537,
        from_address=ADDY_10,
        to_address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        value=0,
        gas=896581,
        gas_price=2000000000,
        gas_used=285898,
        input_data=hexstring_to_bytes('0x1cff79cd000000000000000000000000526af336d614ade5cc252a407062b8861af998f500000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044bc244c11000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af30000000000000000000000000000000000000000000000000000000000025ee100000000000000000000000000000000000000000000000000000000'),
        nonce=25,
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        trace_id=27,
        from_address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
        to_address=ADDY_10,
        value=30000004449579884,
        gas=0,
        gas_used=0,
    )
    receipt = EvmTxReceipt(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=77,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000c41cff79cd000000000000000000000000526af336d614ade5cc252a407062b8861af998f500000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044bc244c11000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af30000000000000000000000000000000000000000000000000000000000025ee100000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
                topics=[
                    hexstring_to_bytes('0x1cff79cd00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000720972dc53741a72fee22400828122836640a74b'),
                    hexstring_to_bytes('0x000000000000000000000000526af336d614ade5cc252a407062b8861af998f5'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000040'),
                ],
            ), EvmTxReceiptLog(
                log_index=78,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024f7c8d6340000000000000000000000000000000000000000000000000000000000025ee1'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xf7c8d63400000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=79,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044a5cd184e0000000000000000000000000000000000000000000000000000000000025ee1000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xa5cd184e00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                ],
            ), EvmTxReceiptLog(
                log_index=80,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=81,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004495d32cb'),
                address=string_to_evm_address('0x9B0F70Df76165442ca6092939132bBAEA77f2d7A'),
                topics=[
                    hexstring_to_bytes('0x495d32cb00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=82,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000044a5cd184e0000000000000000000000000000000000000000000000000000000000025ee1000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xa5cd184e00000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                ],
            ), EvmTxReceiptLog(
                log_index=83,
                data=hexstring_to_bytes('0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                ],
            ), EvmTxReceiptLog(
                log_index=84,
                data=hexstring_to_bytes('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000247f8661a1000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0x7f8661a100000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=85,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006a94d8587a336c'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000448a5065aebb8e423f0896e6c5d525c040f59af3'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=86,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006554ec8a7bea33'),
                address=string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09'),
                topics=[
                    hexstring_to_bytes('0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=87,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000006a94d8587a336c'),
                address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                topics=[
                    hexstring_to_bytes('0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                ],
            ), EvmTxReceiptLog(
                log_index=88,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024b84d21060000000000000000000000000000000000000000000000000000000000025ee1'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb84d210600000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=89,
                data=hexstring_to_bytes('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024b84d21060000000000000000000000000000000000000000000000000000000000025ee1'),
                address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
                topics=[
                    hexstring_to_bytes('0xb84d210600000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x00000000000000000000000072ee0f9ab3678148cc0700243cb38577bd290869'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000025ee1'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(ethereum_transaction_decoder.database)
    with dbevmtx.db.user_write() as cursor:
        dbevmtx.add_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=ADDY_10)
    events, _, _ = ethereum_transaction_decoder._decode_transaction(
        transaction=transaction,
        tx_receipt=receipt,
    )
    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1588030595000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000571796'),
            location_label=ADDY_10,
            notes='Burn 0.000571796 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=1588030595000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal('0.030000004449579884'),
            location_label=ADDY_10,
            notes='Withdraw 0.030000004449579884 ETH from CDP 155361',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x72Ee0f9AB3678148CC0700243CB38577Bd290869'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=90,
            timestamp=1588030595000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label='0x72Ee0f9AB3678148CC0700243CB38577Bd290869',
            notes='Close CDP 155361',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xca482bCd75A6E0697aD6A1732aa187310b8372Df']])
def test_makerdao_sai_cdp_migration(ethereum_transaction_decoder, ethereum_accounts):
    """Check that a Sai CDP migration is decoded properly"""
    tx_hash = deserialize_evm_tx_hash('0x03620c6bf5edb7a7935953337ffcfac70d631cf2012d6c80d36828d636063318 ')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            amount=FVal('0.022255814'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes='Withdraw 0.022255814 ETH from ETH-A MakerDAO vault',
            counterparty=CPT_VAULT,
            address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            extra_data={'vault_type': 'ETH-A'},
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('0.022255814'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes='Send 0.022255814 ETH to 0x22953B20aB21eF5b2A28c1bB55734fB2525Ebaf2',
            address=string_to_evm_address('0x22953B20aB21eF5b2A28c1bB55734fB2525Ebaf2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=41,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_SAI,
            amount=FVal('242.093537946269468696'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes='Borrow 242.093537946269468696 SAI from CDP 19125',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x22953B20aB21eF5b2A28c1bB55734fB2525Ebaf2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=51,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SAI,
            amount=FVal('242.093537946269468696'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes='Send 242.093537946269468696 SAI from 0xca482bCd75A6E0697aD6A1732aa187310b8372Df to 0xcb0C7C757C64e1583bA5673dE486BDe1b8329879',  # noqa: E501
            address=string_to_evm_address('0xcb0C7C757C64e1583bA5673dE486BDe1b8329879'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=52,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
            amount=FVal('0.459550053455645351'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes='Receive 0.459550053455645351 MKR from 0x39755357759cE0d7f32dC8dC45414CCa409AE24e to 0xca482bCd75A6E0697aD6A1732aa187310b8372Df',  # noqa: E501
            address=string_to_evm_address('0x39755357759cE0d7f32dC8dC45414CCa409AE24e'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=58,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:1/erc20:0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'),
            amount=FVal('0.45955005345564535'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes=f'Send 0.45955005345564535 MKR from 0xca482bCd75A6E0697aD6A1732aa187310b8372Df to {MAKERDAO_MIGRATION_ADDRESS}',  # noqa: E501
            address=MAKERDAO_MIGRATION_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=65,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=MAKERDAO_MIGRATION_ADDRESS,
            notes='Close CDP 19125',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x22953B20aB21eF5b2A28c1bB55734fB2525Ebaf2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=102,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_WETH,
            amount=FVal('0.022255814'),
            location_label='0xca482bCd75A6E0697aD6A1732aa187310b8372Df',
            notes='Receive 0.022255814 WETH from 0x2F0b23f53734252Bda2277357e97e1517d6B042A to 0xca482bCd75A6E0697aD6A1732aa187310b8372Df',  # noqa: E501
            address=string_to_evm_address('0x2F0b23f53734252Bda2277357e97e1517d6B042A'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=105,
            timestamp=1579044372000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Migrate Sai CDP 19125 to Dai CDP 3768',
            counterparty=CPT_SAI,
            address=string_to_evm_address('0x22953B20aB21eF5b2A28c1bB55734fB2525Ebaf2'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2D3f907b0cF2C7D3c2BA4Cbc72971081FfCea963']])
def test_sai_dai_migration(ethereum_transaction_decoder, ethereum_accounts):
    """Check that SAI to DAI migration is decoded properly"""
    tx_hash = deserialize_evm_tx_hash('0x1f1f65d04c9c0de8b39d574380851c0e2f9b2552c9aedd71ff56459e2b83cf5c')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1575726133000)
    gas_str = '0.0018393'
    amount_str = '12.559504275171697953'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=33,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_SAI,
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Migrate {amount_str} SAI to DAI',
            counterparty=CPT_MAKERDAO_MIGRATION,
            address=MAKERDAO_MIGRATION_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=39,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Receive {amount_str} DAI from SAI->DAI migration',
            counterparty=CPT_MAKERDAO_MIGRATION,
            address=MAKERDAO_MIGRATION_ADDRESS,
        ),
    ]
    assert events == expected_events
