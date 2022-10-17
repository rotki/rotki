import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_LQTY, A_LUSD
from rotkehlchen.constants.misc import EXP18, ZERO
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    EvmInternalTransaction,
    EvmTransaction,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hexbytes import hexstring_to_bytes


@pytest.mark.parametrize('ethereum_accounts', [['0x9ba961989Dd6609Ed091f512bE947118c40F2291']])  # noqa: E501
def test_liquity_trove_adjust(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0xdb9a541a4af7d5d46d7ea5fe4a2a752dcb731d64d052f86f630e97362063602c
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xdb9a541a4af7d5d46d7ea5fe4a2a752dcb731d64d052f86f630e97362063602c'
    user_address = '0x9ba961989Dd6609Ed091f512bE947118c40F2291'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address=user_address,
        to_address='0x24179cd81c9e782a4096035f7ec97fb8b783e007',
        value=FVal('2.1') * EXP18,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xc6a6cf2000000000000000000000000000000000000000000000000000238e8a8455758900000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001018f9e3f8eea75e0100000000000000000000000000000000000000000000000000000000000000001000000000000000000000000e24328e7df3d87c1cbcc9043326f9b20c425a9e6000000000000000000000000de64f98baece7282973ce8d67cd73455d4748673'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=91,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000014a3a4295480654a6'),  # noqa: E501
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=95,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000021e19de846fc75de296000000000000000000000000000000000000000000000000429d069189e00000000000000000000000000000000000000000000000000000429d069189e000000000000000000000000000000000000000000000000000000000000000000002'),  # noqa: E501
                address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc3770d654ed33aeea6bf11ac8ef05d02a6a04ed4686dd2f624d853bbec43cc8b'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009ba961989dd6609ed091f512be947118c40f2291'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=98,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000001018f9e3f8eea75e010'),  # noqa: E501
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000009ba961989dd6609ed091f512be947118c40f2291'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=99,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000004e97821fe7ced4f8b2fb'),  # noqa: E501
                address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xca232b5abb988c540b959ff6c3bfae3e97fff964fd098c508f9613c0a6bf1a80'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('2.1'), usd_value=ZERO),
            location_label=user_address,
            notes='Deposit 2.1 ETH as collateral for liquity',
            counterparty='liquity',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=100,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_LUSD,
            balance=Balance(amount=FVal('4751.162005820150243344'), usd_value=ZERO),
            location_label=user_address,
            notes='Generate 4751.162005820150243344 LUSD from liquity',
            counterparty='liquity',
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x648E180e246741363639B1496762763dd25649db']])  # noqa: E501
def test_liquity_trove_deposit_lusd(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x40bb08427a3b99fb9896cf14858d82d361a6e7a8fb7dd6d2000511ac3dca5707
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x40bb08427a3b99fb9896cf14858d82d361a6e7a8fb7dd6d2000511ac3dca5707'
    user_address = '0x648E180e246741363639B1496762763dd25649db'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address=user_address,
        to_address='0x24179cd81c9e782a4096035f7ec97fb8b783e007',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xc6a6cf200000000000000000000000000000000000000000000000000023c5d78add1ce10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001906c5721af5fbe700000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000de9ac8262766e73a1d5f75cc3c37ae495e88d225000000000000000000000000cb926f497763ea5cf993912a442431e6a91d5a64'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=204,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000038f9ba4f4e8bb875c546b0000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000000000000000000002'),  # noqa: E501
                address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc3770d654ed33aeea6bf11ac8ef05d02a6a04ed4686dd2f624d853bbec43cc8b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=207,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000001906c5721af5fbe70000'),  # noqa: E501
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=208,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000004e900a6a97e3873abb07'),  # noqa: E501
                address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xca232b5abb988c540b959ff6c3bfae3e97fff964fd098c508f9613c0a6bf1a80'),  # noqa: E501
                ],
            ),
        ],
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=208,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_LUSD,
            balance=Balance(amount=FVal('118184.07'), usd_value=ZERO),
            location_label=user_address,
            notes='Return 118184.07 LUSD to liquity',
            counterparty='liquity',
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0x648E180e246741363639B1496762763dd25649db']])  # noqa: E501
def test_liquity_trove_remove_eth(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x6be5312c21855c3cc324b5b6ce9f9f65dbd488e270e84ac5e6fb96c74d83fe4e
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x6be5312c21855c3cc324b5b6ce9f9f65dbd488e270e84ac5e6fb96c74d83fe4e'
    user_address = '0x648E180e246741363639B1496762763dd25649db'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address=user_address,
        to_address='0x24179cd81c9e782a4096035f7ec97fb8b783e007',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0xc6a6cf2000000000000000000000000000000000000000000000000000238811c2e89e1b000000000000000000000000000000000000000000000001bc16d674ec80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000cb926f497763ea5cf993912a442431e6a91d5a64000000000000000000000000c68d61757a9894f34871c0ae733ac034d9abf807'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=204,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000038f9ba4f4e8bb875c546b0000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000aed129e69968ff40000000000000000000000000000000000000000000000000000000000000000002'),  # noqa: E501
                address=string_to_evm_address('0x24179CD81c9e782A4096035f7eC97fB8B783e007'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xc3770d654ed33aeea6bf11ac8ef05d02a6a04ed4686dd2f624d853bbec43cc8b'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=293,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000648e180e246741363639b1496762763dd25649db'),  # noqa: E501
                    hexstring_to_bytes('0x0000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=208,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000004e927b246c443a2daac9'),  # noqa: E501
                address=string_to_evm_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xca232b5abb988c540b959ff6c3bfae3e97fff964fd098c508f9613c0a6bf1a80'),  # noqa: E501
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        trace_id=19,
        timestamp=Timestamp(1646375440),
        block_number=10182160,
        from_address='0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F',
        to_address=user_address,
        value=FVal(32) * EXP18,
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx], relevant_address=user_address)  # noqa: E501
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal('32'), usd_value=ZERO),
            location_label=user_address,
            notes='Withdraw 32 ETH collateral from liquity',
            counterparty='liquity',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=295,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_LUSD,
            balance=Balance(amount=FVal('0'), usd_value=ZERO),
            location_label=user_address,
            notes='Return 0 LUSD to liquity',
            counterparty='liquity',
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xF04E6f2D27ED324917AD2098F96f5d4ac52e1684']])  # noqa: E501
def test_liquity_pool_deposit(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0x1277cb6c2c8e151fe90118cdd738e46f894e18de04ab6af33d567e91597f322b
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0x1277cb6c2c8e151fe90118cdd738e46f894e18de04ab6af33d567e91597f322b'
    user_address = '0xF04E6f2D27ED324917AD2098F96f5d4ac52e1684'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address=user_address,
        to_address='0x66017D22b0f8556afDd19FC67041899Eb65a21bb',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x5f788d650000000000000000000000000000000000000000000000068155a43676e0000000000000000000000000000030e5d10dc30a0ce2545a4dbe8de4fcba590062c5'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=907,
                data=hexstring_to_bytes('0x0000000000000000000000000000000000000000000000068155a43676e00000'),  # noqa: E501
                address=string_to_evm_address('0x5f98805A4E8be255a32880FDeC7F6728C6568bA0'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f04e6f2d27ed324917ad2098f96f5d4ac52e1684'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=911,
                data=hexstring_to_bytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
                address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x51457222ebca92c335c9c86e2baa1cc0e40ffaa9084a51452980d5ba8dec2f63'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f04e6f2d27ed324917ad2098f96f5d4ac52e1684'),  # noqa: E501
                ],
            ),
        ],
    )
    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)
    assert len(events) == 2
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=908,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_LUSD,
            balance=Balance(amount=FVal('120'), usd_value=ZERO),
            location_label=user_address,
            notes="Deposit 120 LUSD in liquity's stability pool",
            counterparty='liquity',
        )]
    assert events == expected_events


@pytest.mark.parametrize('ethereum_accounts', [['0xF03639047f75204d00c9314611C2b24570db4405']])  # noqa: E501
def test_liquity_pool_remove_deposits(database, ethereum_manager, eth_transactions):
    """
    Data for deposit taken from
    https://etherscan.io/tx/0xad077faf7976504615561ac7fd9fdddc934180f3237f216851136d2327d71196
    Deposit 2.1 ether and borrow 4752 LUSD
    """
    msg_aggregator = MessagesAggregator()
    tx_hex = '0xad077faf7976504615561ac7fd9fdddc934180f3237f216851136d2327d71196'
    user_address = '0xF03639047f75204d00c9314611C2b24570db4405'
    evmhash = deserialize_evm_tx_hash(tx_hex)
    transaction = EvmTransaction(
        tx_hash=evmhash,
        timestamp=1646375440,
        block_number=14318825,
        from_address=user_address,
        to_address='0x66017D22b0f8556afDd19FC67041899Eb65a21bb',
        value=0,
        gas=171249,
        gas_price=22990000000,
        gas_used=171249,
        input_data=hexstring_to_bytes('0x2e54bf950000000000000000000000000000000000000000000000000000000000000000'),  # noqa: E501
        nonce=507,
    )
    receipt = EthereumTxReceipt(
        tx_hash=evmhash,
        contract_address=None,
        status=True,
        type=0,
        logs=[
            EthereumTxReceiptLog(
                log_index=131,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000bfa91a19de91add4'),  # noqa: E501
                address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d8c9d9071123a059c6e0a945cf0e0c82b508d816'),  # noqa: E501
                    hexstring_to_bytes('0x00000000000000000000000003cd116cabe0747f31a71b3565877717097fc06c'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=133,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000046f454ff5d19ab0efd'),  # noqa: E501
                address=string_to_evm_address('0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000d8c9d9071123a059c6e0a945cf0e0c82b508d816'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f03639047f75204d00c9314611c2b24570db4405'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=134,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000046f454ff5d19ab0efd'),  # noqa: E501
                address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x2608b986a6ac0f6c629ca37018e80af5561e366252ae93602a96d3ab2e73e42d'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f03639047f75204d00c9314611c2b24570db4405'),  # noqa: E501
                ],
            ), EthereumTxReceiptLog(
                log_index=208,
                data=hexstring_to_bytes('0x000000000000000000000000000000000000000000000000004b0e79ddb72c200000000000000000000000000000000000000000000000014acf0eec96f96a1c'),  # noqa: E501
                address=string_to_evm_address('0x66017D22b0f8556afDd19FC67041899Eb65a21bb'),
                removed=False,
                topics=[
                    hexstring_to_bytes('0x51457222ebca92c335c9c86e2baa1cc0e40ffaa9084a51452980d5ba8dec2f63'),  # noqa: E501
                    hexstring_to_bytes('0x000000000000000000000000f03639047f75204d00c9314611c2b24570db4405'),  # noqa: E501
                ],
            ),
        ],
    )
    internal_tx = EvmInternalTransaction(
        parent_tx_hash=evmhash,
        trace_id=19,
        timestamp=Timestamp(1646375440),
        block_number=10182160,
        from_address='0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F',
        to_address=user_address,
        value=FVal(0.0211265398269) * EXP18,
    )

    dbethtx = DBEthTx(database)
    with database.user_write() as cursor:
        dbethtx.add_ethereum_transactions(cursor, [transaction], relevant_address=None)
        dbethtx.add_ethereum_internal_transactions(cursor, [internal_tx], relevant_address=user_address)  # noqa: E501
        decoder = EVMTransactionDecoder(
            database=database,
            ethereum_manager=ethereum_manager,
            transactions=eth_transactions,
            msg_aggregator=msg_aggregator,
        )
        events = decoder.decode_transaction(cursor, transaction=transaction, tx_receipt=receipt)

    assert len(events) == 3
    expected_events = [
        HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=0,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
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
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=1,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0211265398269'), usd_value=ZERO),
            location_label=user_address,
            notes="Collect 0.0211265398269 ETH from liquity's stability pool",
            counterparty='liquity',
        ), HistoryBaseEntry(
            event_identifier=evmhash,
            sequence_index=135,
            timestamp=1646375440000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_LQTY,
            balance=Balance(amount=FVal('1308.878062778294406909'), usd_value=ZERO),
            location_label=user_address,
            notes="Collect 1308.878062778294406909 LQTY from liquity's stability pool",
            counterparty='liquity',
        )]
    assert events == expected_events
