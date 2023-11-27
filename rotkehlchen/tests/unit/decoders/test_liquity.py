import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.constants.misc import EXP18
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import LIQUITY_STAKING_DETAILS, EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    EvmInternalTransaction,
    EvmTransaction,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x9ba961989Dd6609Ed091f512bE947118c40F2291']])
def test_liquity_trove_adjust(database, ethereum_inquirer, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0xdb9a541a4af7d5d46d7ea5fe4a2a752dcb731d64d052f86f630e97362063602c
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    tx_hex = '0xdb9a541a4af7d5d46d7ea5fe4a2a752dcb731d64d052f86f630e97362063602c'
    user_address = string_to_evm_address('0x9ba961989Dd6609Ed091f512bE947118c40F2291')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x24179cd81c9e782a4096035f7ec97fb8b783e007'),
        value=(FVal('2.1') * EXP18).to_int(exact=True),
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xc6a6cf2000000000000000000000000000000000000000000000000000238e8a8455758900000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001018f9e3f8eea75e0100000000000000000000000000000000000000000000000000000000000000001000000000000000000000000e24328e7df3d87c1cbcc9043326f9b20c425a9e6000000000000000000000000de64f98baece7282973ce8d67cd73455d4748673'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=91,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000014a3a4295480654a6'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d'),
                ],
            ), EvmTxReceiptLog(
                log_index=95,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000021e19de846fc75de296000000000000000000000000000000000000000000000000429d069189e00000000000000000000000000000000000000000000000000000429d069189e000000000000000000000000000000000000000000000000000000000000000000002'),
                address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc3770d654ed33aeea6bf11ac8ef05d02a6a04ed4686dd2f624d853bbec43cc8b'),
                    hexstring_to_bytes('0x0000000000000000000000009ba961989dd6609ed091f512be947118c40f2291'),
                ],
            ), EvmTxReceiptLog(
                log_index=98,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000001018f9e3f8eea75e010'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                    hexstring_to_bytes('0x0000000000000000000000009ba961989dd6609ed091f512be947118c40f2291'),
                ],
            ), EvmTxReceiptLog(
                log_index=99,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000004e97821fe7ced4f8b2fb'),
                address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xca232b5abb988c540b959ff6c3bfae3e97fff964fd098c508f9613c0a6bf1a80'),
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('2.1'), usd_value=ZERO),
            location_label=user_address,
            notes='Deposit 2.1 ETH as collateral for liquity',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x24179cd81c9e782a4096035f7ec97fb8b783e007'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=100,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_LUSD,
            balance=Balance(amount=FVal('4751.162005820150243344'), usd_value=ZERO),
            location_label=user_address,
            notes='Generate 4751.162005820150243344 LUSD from liquity',
            counterparty=CPT_LIQUITY,
            address=ZERO_ADDRESS,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x648E180e246741363639B1496762763dd25649db']])
def test_liquity_trove_deposit_lusd(database, ethereum_inquirer, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x40bb08427a3b99fb9896cf14858d82d361a6e7a8fb7dd6d2000511ac3dca5707
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    tx_hex = '0x40bb08427a3b99fb9896cf14858d82d361a6e7a8fb7dd6d2000511ac3dca5707'
    user_address = string_to_evm_address('0x648E180e246741363639B1496762763dd25649db')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x24179cd81c9e782a4096035f7ec97fb8b783e007'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xc6a6cf200000000000000000000000000000000000000000000000000023c5d78add1ce10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001906c5721af5fbe700000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000de9ac8262766e73a1d5f75cc3c37ae495e88d225000000000000000000000000cb926f497763ea5cf993912a442431e6a91d5a64'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=204,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000038f9ba4f4e8bb875c546b0000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000000000000000000002'),
                address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc3770d654ed33aeea6bf11ac8ef05d02a6a04ed4686dd2f624d853bbec43cc8b'),
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),
                ],
            ), EvmTxReceiptLog(
                log_index=207,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000001906c5721af5fbe70000'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=208,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000004e900a6a97e3873abb07'),
                address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xca232b5abb988c540b959ff6c3bfae3e97fff964fd098c508f9613c0a6bf1a80'),
                ],
            ),
        ],
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=208,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_LUSD,
            balance=Balance(amount=FVal('118184.07'), usd_value=ZERO),
            location_label=user_address,
            notes='Return 118184.07 LUSD to liquity',
            counterparty=CPT_LIQUITY,
            address=ZERO_ADDRESS,
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x648E180e246741363639B1496762763dd25649db']])
def test_liquity_trove_remove_eth(database, ethereum_inquirer, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x6be5312c21855c3cc324b5b6ce9f9f65dbd488e270e84ac5e6fb96c74d83fe4e
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    tx_hex = '0x6be5312c21855c3cc324b5b6ce9f9f65dbd488e270e84ac5e6fb96c74d83fe4e'
    user_address = string_to_evm_address('0x648E180e246741363639B1496762763dd25649db')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x24179cd81c9e782a4096035f7ec97fb8b783e007'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xc6a6cf2000000000000000000000000000000000000000000000000000238811c2e89e1b000000000000000000000000000000000000000000000001bc16d674ec80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000cb926f497763ea5cf993912a442431e6a91d5a64000000000000000000000000c68d61757a9894f34871c0ae733ac034d9abf807'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=204,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000038f9ba4f4e8bb875c546b0000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000000000000000000002'),
                address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc3770d654ed33aeea6bf11ac8ef05d02a6a04ed4686dd2f624d853bbec43cc8b'),
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),
                ],
            ), EvmTxReceiptLog(
                log_index=293,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                ],
            ), EvmTxReceiptLog(
                log_index=208,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000004e927b246c443a2daac9'),
                address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xca232b5abb988c540b959ff6c3bfae3e97fff964fd098c508f9613c0a6bf1a80'),
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=19,
        from_address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
        to_address=user_address,
        value=(FVal(32) * EXP18).to_int(exact=True),
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=user_address)
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
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('32'), usd_value=ZERO),
            location_label=user_address,
            notes='Withdraw 32 ETH collateral from liquity',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
        ),
    ]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xF04E6f2D27ED324917AD2098F96f5d4ac52e1684']])
def test_liquity_pool_deposit(database, ethereum_inquirer, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x1277cb6c2c8e151fe90118cdd738e46f894e18de04ab6af33d567e91597f322b
    """
    tx_hex = '0x1277cb6c2c8e151fe90118cdd738e46f894e18de04ab6af33d567e91597f322b'
    user_address = string_to_evm_address('0xF04E6f2D27ED324917AD2098F96f5d4ac52e1684')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x5f788d650000000000000000000000000000000000000000000000068155a43676e0000000000000000000000000000030e5d10dc30a0ce2545a4dbe8de4fcba590062c5'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=907,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000068155a43676e00000'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000f04e6f2d27ed324917ad2098f96f5d4ac52e1684'),
                    hexstring_to_bytes('0x00000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb'),
                ],
            ), EvmTxReceiptLog(
                log_index=911,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x51457222ebca92c335c9c86e2baa1cc0e40ffaa9084a51452980d5ba8dec2f63'),
                    hexstring_to_bytes('0x000000000000000000000000f04e6f2d27ed324917ad2098f96f5d4ac52e1684'),
                ],
            ),
        ],
    )
    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=908,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            balance=Balance(amount=FVal('120'), usd_value=ZERO),
            location_label=user_address,
            notes="Deposit 120 LUSD in liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xF03639047f75204d00c9314611C2b24570db4405']])
def test_liquity_pool_remove_deposits(database, ethereum_inquirer, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0xad077faf7976504615561ac7fd9fdddc934180f3237f216851136d2327d71196
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    tx_hex = '0xad077faf7976504615561ac7fd9fdddc934180f3237f216851136d2327d71196'
    user_address = string_to_evm_address('0xF03639047f75204d00c9314611C2b24570db4405')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e54bf950000000000000000000000000000000000000000000000000000000000000000'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=131,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000bfa91a19de91add4'),
                address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000d8c9d9071123a059c6e0a945cf0e0c82b508d816'),
                    hexstring_to_bytes('0x00000000000000000000000003cd116cabe0747f31a71b3565877717097fc06c'),
                ],
            ), EvmTxReceiptLog(
                log_index=133,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000046f454ff5d19ab0efd'),
                address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x000000000000000000000000d8c9d9071123a059c6e0a945cf0e0c82b508d816'),
                    hexstring_to_bytes('0x000000000000000000000000f03639047f75204d00c9314611c2b24570db4405'),
                ],
            ), EvmTxReceiptLog(
                log_index=134,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000046f454ff5d19ab0efd'),
                address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x2608b986a6ac0f6c629ca37018e80af5561e366252ae93602a96d3ab2e73e42d'),
                    hexstring_to_bytes('0x000000000000000000000000f03639047f75204d00c9314611c2b24570db4405'),
                ],
            ), EvmTxReceiptLog(
                log_index=208,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000004b0e79ddb72c200000000000000000000000000000000000000000000000014acf0eec96f96a1c'),
                address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x51457222ebca92c335c9c86e2baa1cc0e40ffaa9084a51452980d5ba8dec2f63'),
                    hexstring_to_bytes('0x000000000000000000000000f03639047f75204d00c9314611c2b24570db4405'),
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=19,
        from_address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
        to_address=user_address,
        value=(FVal(0.0211265398269) * EXP18).to_int(exact=True),
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=user_address)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0211265398269'), usd_value=ZERO),
            location_label=user_address,
            notes="Collect 0.0211265398269 ETH from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=135,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            balance=Balance(amount=FVal('1308.878062778294406909'), usd_value=ZERO),
            location_label=user_address,
            notes="Collect 1308.878062778294406909 LQTY from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0xD8c9D9071123a059C6E0A945cF0e0c82b508d816'),
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x1b63708eafa610DFa81c6DB4A257570D78a6dF1c']])
def test_increase_liquity_staking(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x4e2bbc53a75fbbc954fc305f7adf68be1fa3b1416c941b0350719cc484c9d8fb
    """
    tx_hex = '0x4e2bbc53a75fbbc954fc305f7adf68be1fa3b1416c941b0350719cc484c9d8fb'
    user_address = string_to_evm_address('0x1b63708eafa610DFa81c6DB4A257570D78a6dF1c')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e54bf950000000000000000000000000000000000000000000000000000000000000000'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=175,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000004e1003b28d9278ad0'),
                address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000001b63708eafa610dfa81c6db4a257570d78a6df1c'),
                    hexstring_to_bytes('0x0000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d'),
                ],
            ), EvmTxReceiptLog(
                log_index=176,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000009526ca4eab82bb1e0'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x39df0e5286a3ef2f42a0bf52f32cfe2c58e5b0405f47fe512f2c2439e4cfe204'),
                    hexstring_to_bytes('0x0000000000000000000000001b63708eafa610dfa81c6db4a257570d78a6df1c'),
                ],
            ), EvmTxReceiptLog(
                log_index=177,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000fc03eaf5c09ca0400000000000000000000000000000000000000000000000000002b43068fee11'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xf744d34ca1cb25acfa4180df5f09a67306107110a9f4b6ed99bb3be259738215'),
                    hexstring_to_bytes('0x0000000000000000000000001b63708eafa610dfa81c6db4a257570d78a6df1c'),
                ],
            ), EvmTxReceiptLog(
                log_index=178,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000fc03eaf5c09ca04'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d'),
                    hexstring_to_bytes('0x0000000000000000000000001b63708eafa610dfa81c6db4a257570d78a6df1c'),
                ],
            ), EvmTxReceiptLog(
                log_index=179,
                data=hexstring_to_bytes('0x0000000000000000000000001b63708eafa610dfa81c6db4a257570d78a6df1c00000000000000000000000000000000000000000000000000002b43068fee11'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x6109e2559dfa766aaec7118351d48a523f0a4157f49c8d68749c8ac41318ad12'),
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=19,
        from_address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        to_address=user_address,
        value=(FVal(0.000047566872899089) * EXP18).to_int(exact=True),
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=user_address)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000047566872899089'), usd_value=ZERO),
            location_label=user_address,
            notes="Receive reward of 0.000047566872899089 ETH from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=177,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LQTY,
            balance=Balance(amount=FVal('89.99999999999997'), usd_value=ZERO),
            location_label=user_address,
            notes='Stake 89.99999999999997 LQTY in the Liquity protocol',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
            extra_data={LIQUITY_STAKING_DETAILS: {'staked_amount': '171.95999999999998', 'asset': A_LQTY}},  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=180,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LUSD,
            balance=Balance(amount=FVal('1.134976028981709316'), usd_value=ZERO),
            location_label=user_address,
            notes="Receive reward of 1.134976028981709316 LUSD from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x58D9A499AC82D74b08b3Cb76E69d8f32e1395746']])
def test_remove_liquity_staking(database, ethereum_inquirer, eth_transactions):
    """
    Data taken from
    https://etherscan.io/tx/0x028397f0409042da26890ec27eb36d617e326c3ce476d823f181419bdd0ad860
    """
    tx_hex = '0x028397f0409042da26890ec27eb36d617e326c3ce476d823f181419bdd0ad860'
    user_address = string_to_evm_address('0x58D9A499AC82D74b08b3Cb76E69d8f32e1395746')
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1646375440),
        block_number=14318825,
        from_address=user_address,
        to_address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e54bf950000000000000000000000000000000000000000000000000000000000000000'),
        nonce=507,
    )
    receipt = EvmTxReceipt(
        tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EvmTxReceiptLog(
                log_index=117,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000001436cd1562e364c2b1'),
                address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d'),
                    hexstring_to_bytes('0x00000000000000000000000058d9a499ac82d74b08b3cb76e69d8f32e1395746'),
                ],
            ), EvmTxReceiptLog(
                log_index=118,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x39df0e5286a3ef2f42a0bf52f32cfe2c58e5b0405f47fe512f2c2439e4cfe204'),
                    hexstring_to_bytes('0x00000000000000000000000058d9a499ac82d74b08b3cb76e69d8f32e1395746'),
                ],
            ), EvmTxReceiptLog(
                log_index=119,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000225fa30dbe8060180000000000000000000000000000000000000000000000000000c3b8a0f244e8'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xf744d34ca1cb25acfa4180df5f09a67306107110a9f4b6ed99bb3be259738215'),
                    hexstring_to_bytes('0x00000000000000000000000058d9a499ac82d74b08b3cb76e69d8f32e1395746'),
                ],
            ), EvmTxReceiptLog(
                log_index=120,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000225fa30dbe806018'),
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),
                    hexstring_to_bytes('0x0000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d'),
                    hexstring_to_bytes('0x00000000000000000000000058d9a499ac82d74b08b3cb76e69d8f32e1395746'),
                ],
            ), EvmTxReceiptLog(
                log_index=121,
                data=hexstring_to_bytes('0x00000000000000000000000058d9a499ac82d74b08b3cb76e69d8f32e13957460000000000000000000000000000000000000000000000000000c3b8a0f244e8'),
                address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x6109e2559dfa766aaec7118351d48a523f0a4157f49c8d68749c8ac41318ad12'),
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        chain_id=ChainID.ETHEREUM,
        trace_id=19,
        from_address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        to_address=user_address,
        value=(FVal(0.000215197741630696) * EXP18).to_int(exact=True),
    )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as cursor:
        dbevmtx.add_evm_transactions(cursor, [transaction], relevant_address=None)
        dbevmtx.add_evm_internal_transactions(cursor, [internal_tx], relevant_address=user_address)
    decoder = EthereumTransactionDecoder(
        database=database,
        ethereum_inquirer=ethereum_inquirer,
        transactions=eth_transactions,
    )
    events, _ = decoder._decode_transaction(transaction=transaction, tx_receipt=receipt)

    assert len(events) == 4
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(
                amount=FVal(0.00393701451),
                usd_value=ZERO,
            ),
            location_label=user_address,
            notes='Burned 0.00393701451 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000215197741630696'), usd_value=ZERO),
            location_label=user_address,
            notes="Receive reward of 0.000215197741630696 ETH from Liquity's staking",
            address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
            counterparty=CPT_LIQUITY,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=119,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_LQTY,
            balance=Balance(amount=FVal('372.883717436930835121'), usd_value=ZERO),
            location_label=user_address,
            notes='Unstake 372.883717436930835121 LQTY from the Liquity protocol',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
            extra_data={LIQUITY_STAKING_DETAILS: {'staked_amount': '0', 'asset': A_LQTY}},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=122,
            timestamp=TimestampMS(1646375440000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LUSD,
            balance=Balance(amount=FVal('2.476877599503048728'), usd_value=ZERO),
            location_label=user_address,
            notes="Receive reward of 2.476877599503048728 LUSD from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x4f9Fbb3f1E99B56e0Fe2892e623Ed36A76Fc605d'),
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5DD596C901987A2b28C38A9C1DfBf86fFFc15d77']])
def test_stability_pool_withdrawal(database, ethereum_inquirer, ethereum_accounts):
    address = ethereum_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xca9acc377ba5eb020dd5f113961016ac1c652617b0e5c71f31a7fb32e188858d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1677402143000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00719440411023624')),
            location_label=address,
            notes='Burned 0.00719440411023624 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=191,
            timestamp=TimestampMS(1677402143000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            balance=Balance(amount=FVal('1.3168840890645')),
            location_label=address,
            notes="Collect 1.3168840890645 LQTY from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0xD8c9D9071123a059C6E0A945cF0e0c82b508d816'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=195,
            timestamp=TimestampMS(1677402143000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_LUSD,
            balance=Balance(amount=FVal('500000')),
            location_label=address,
            notes="Withdraw 500000 LUSD from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0c3ce74FCB2B93F9244544919572818Dc2AC0641']])
def test_ds_proxy_liquity_deposit(database, ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    evmhash = deserialize_evm_tx_hash('0x83e9930bee6a993204ade072ac6753249f9773b0da243b7efdb6cbba1e0bff6c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1664055431000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002962168608405875')),
            location_label=user_address,
            notes='Burned 0.002962168608405875 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=291,
            timestamp=TimestampMS(1664055431000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            balance=Balance(amount=FVal('87.49718915849563905')),
            location_label=user_address,
            notes="Deposit 87.49718915849563905 LUSD in liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=292,
            timestamp=TimestampMS(1664055431000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_LUSD,
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=user_address,
            notes='Set LUSD spending approval of 0x0c3ce74FCB2B93F9244544919572818Dc2AC0641 by 0x7815beb98a927565eA43b5854644392F21dA0021 to 115792089237316195423570985000000000000000000000000000000000',  # noqa: E501
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0c3ce74FCB2B93F9244544919572818Dc2AC0641']])
def test_ds_proxy_liquity_withdraw(database, ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    evmhash = deserialize_evm_tx_hash('0xdac8d9273a17b00fb81e89839d0c974e393db406a641552051419646b902c4b3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002590429704686116')),
            location_label=user_address,
            notes='Burned 0.002590429704686116 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000033225735796413')),
            location_label=user_address,
            notes="Collect 0.000033225735796413 ETH from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=245,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_LUSD,
            balance=Balance(amount=FVal('87.456384085561687234')),
            location_label=user_address,
            notes="Withdraw 87.456384085561687234 LUSD from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=247,
            timestamp=TimestampMS(1665138455000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            balance=Balance(amount=FVal('0.233230483618895237')),
            location_label=user_address,
            notes="Collect 0.233230483618895237 LQTY from liquity's stability pool",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x7815beb98a927565eA43b5854644392F21dA0021'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xEa00FC641a817e5F3eded4743aac7AB08dbf74b0']])
def test_ds_proxy_liquity_staking(database, ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    evmhash = deserialize_evm_tx_hash('0x48aa71f1af847d93601f03777ba960281bc9405bbdcc2fdb8c64f2a3350f354a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.009100878613428384')),
            location_label=user_address,
            notes='Burned 0.009100878613428384 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000000820336735695')),
            location_label=user_address,
            notes="Receive reward of 0.000000820336735695 ETH from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=196,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LQTY,
            balance=Balance(amount=FVal('4584.01')),
            location_label=user_address,
            notes='Stake 4584.01 LQTY in the Liquity protocol',
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
            extra_data={
                'liquity_staking': {
                    'staked_amount': '11325.738578026449094146',
                    'asset': 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D',
                },
            },
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=197,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_LQTY,
            balance=Balance(amount=FVal('0')),
            location_label=user_address,
            notes='Revoke LQTY spending approval of 0xEa00FC641a817e5F3eded4743aac7AB08dbf74b0 by 0x31E45D87D9549DCc5cc28925238b7e329719C8fB',  # noqa: E501
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=206,
            timestamp=TimestampMS(1679936291000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LUSD,
            balance=Balance(amount=FVal('6.17725146534640172')),
            location_label=user_address,
            notes="Receive reward of 6.17725146534640172 LUSD from Liquity's staking",
            counterparty=CPT_LIQUITY,
            address=string_to_evm_address('0x31E45D87D9549DCc5cc28925238b7e329719C8fB'),
        ),
    ]
    assert events == expected_events
