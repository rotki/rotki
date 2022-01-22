from typing import TYPE_CHECKING, List, Optional, Tuple

from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.structures import EthereumTxReceipt, EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import ETHTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Location
from rotkehlchen.utils.misc import from_wei, hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


# keccak of Transfer(address,address,uint256)
ERC20_TRANSFER = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501
# keccak of approve(address,uint256)
ERC20_APPROVE = b'\x8c[\xe1\xe5\xeb\xec}[\xd1OqB}\x1e\x84\xf3\xdd\x03\x14\xc0\xf7\xb2)\x1e[ \n\xc8\xc7\xc3\xb9%'  # noqa: E501


class EVMTransactionDecoder():

    def __init__(self, database: 'DBHandler'):
        self.database = database
        self.tracked_accounts = self.database.get_blockchain_accounts()
        self.event_rules = (  # rules for tx receipt logs decoding
            self._maybe_decode_erc20_approve,
            self._maybe_decode_erc20_transfer,
        )

    def try_all_rules(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        for rule in self.event_rules:
            event = rule(token=token, log=log, transaction=transaction)
            if event:
                return event

        return None

    def decode_transaction(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Decodes an ethereum transaction and its receipt and saves result in the DB"""
        cursor = self.database.conn.cursor()
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor.execute('DELETE FROM history_events WHERE event_identifier=?', (tx_hex,))
        cursor.execute(
            'DELETE FROM evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        events = []
        # check if any eth transfer happened in the transaction
        event = self._maybe_decode_simple_transactions(transaction)
        if event is not None:
            events.append(event)

        # decode transaction logs from the receipt
        for tx_log in tx_receipt.logs:
            token = GlobalDBHandler.get_ethereum_token(tx_log.address)
            event = self.try_all_rules(token=token, log=tx_log, transaction=transaction)
            if event:
                events.append(event)

        self.database.add_history_events(events)
        cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_hash, blockchain, value) VALUES(?, ?, ?)',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        self.database.update_last_write()
        return events

    def decode_transaction_hashes(self, hashes: List[bytes]) -> None:
        """Runs the decoding logic for a number of transaction hashes

        Caller must make sure that:
        - The transaction hashes must exist in the DB for transactions
        - The transaction hashes must also have the corresponding receipts in the DB
        """
        # TODO: Change this if transaction filter query can accept multiple hashes
        dbethtx = DBEthTx(self.database)
        for tx_hash in hashes:
            txs = dbethtx.get_ethereum_transactions(
                filter_=ETHTransactionsFilterQuery.make(tx_hash=tx_hash),
                has_premium=True,  # ignore limiting here
            )
            tx_receipt = dbethtx.get_receipt(tx_hash)
            assert tx_receipt, 'The transaction receipt for {tx_hash.hex()} should be in the DB'
            self.decode_transaction(transaction=txs[0], tx_receipt=tx_receipt)

    def get_or_decode_transaction_events(
            self,
            transaction: EthereumTransaction,
            tx_receipt: EthereumTxReceipt,
    ) -> List[HistoryBaseEntry]:
        """Get a transaction's events if existing in the DB or decode them"""
        tx_hex = '0x' + transaction.tx_hash.hex()
        cursor = self.database.conn.cursor()
        results = cursor.execute(
            'SELECT COUNT(*) from evm_tx_mappings WHERE tx_hash=? AND blockchain=? AND value=?',
            (transaction.tx_hash, 'ETH', 'decoded'),
        )
        if results.fetchone()[0] != 0:  # already decoded and in the DB
            events = self.database.get_history_events(
                filter_query=HistoryEventFilterQuery.make(
                    event_identifier=tx_hex,
                ),
                has_premium=True,  # for this function we don't limit anything
            )
            return events

        # else we should decode now
        events = self.decode_transaction(transaction, tx_receipt)
        return events

    def _decode_direction(
            self,
            from_address: ChecksumEthAddress,
            to_address: ChecksumEthAddress,
    ) -> Optional[Tuple[HistoryEventType, str, str]]:
        tracked_from = from_address in self.tracked_accounts.eth
        tracked_to = to_address in self.tracked_accounts.eth
        if not tracked_from and not tracked_to:
            return None

        if tracked_from and tracked_to:
            event_type = HistoryEventType.TRANSFER
            location_label = from_address
            counterparty = to_address
        elif tracked_from:
            event_type = HistoryEventType.SPEND
            location_label = from_address
            counterparty = to_address
        else:  # can only be tracked_to
            event_type = HistoryEventType.RECEIVE
            location_label = to_address
            counterparty = from_address

        return event_type, location_label, counterparty

    def _maybe_decode_simple_transactions(
            self,
            tx: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        if tx.to_address is None:
            if tx.from_address not in self.tracked_accounts.eth:
                return None
            return HistoryBaseEntry(  # contract deployment
                event_identifier='0x' + tx.tx_hash.hex(),
                sequence_index=0,
                timestamp=tx.timestamp,
                location=Location.BLOCKCHAIN,
                location_label=tx.from_address,
                asset_balance=AssetBalance(asset=A_ETH, balance=Balance(amount=amount)),
                notes='Contract deployment',
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DEPLOY,
                counterparty=None,  # TODO: Find out contract address
            )

        if amount == ZERO:
            return None

        direction_result = self._decode_direction(tx.from_address, tx.to_address)
        if direction_result is None:
            return None

        event_type, location_label, counterparty = direction_result
        return HistoryBaseEntry(
            event_identifier='0x' + tx.tx_hash.hex(),
            sequence_index=0,
            timestamp=tx.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset_balance=AssetBalance(asset=A_ETH, balance=Balance(amount=amount)),
            notes=f'Transfer {amount} ETH {tx.from_address} -> {tx.to_address}',
            event_type=event_type,
            event_subtype=None,
            counterparty=counterparty,
        )

    def _maybe_decode_erc20_approve(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] != ERC20_APPROVE or token is None:
            return None

        owner_address = hex_or_bytes_to_address(log.topics[1])
        spender_address = hex_or_bytes_to_address(log.topics[2])

        if not any(x in self.tracked_accounts.eth for x in (owner_address, spender_address)):
            return None

        amount_raw = hex_or_bytes_to_int(log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Approve {amount} {token.symbol} of {owner_address} for spending by {spender_address}'  # noqa: E501
        return HistoryBaseEntry(
            event_identifier='0x' + transaction.tx_hash.hex(),
            sequence_index=log.log_index,
            timestamp=transaction.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=owner_address,
            asset_balance=AssetBalance(asset=token, balance=Balance(amount=amount)),
            notes=notes,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            counterparty=spender_address,
        )

    def _maybe_decode_erc20_transfer(
            self,
            token: Optional[EthereumToken],
            log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,
    ) -> Optional[HistoryBaseEntry]:
        if log.topics[0] != ERC20_TRANSFER or token is None:
            return None

        from_address = hex_or_bytes_to_address(log.topics[1])
        to_address = hex_or_bytes_to_address(log.topics[2])
        direction_result = self._decode_direction(from_address, to_address)
        if direction_result is None:
            return None

        event_type, location_label, counterparty = direction_result
        amount_raw = hex_or_bytes_to_int(log.data)
        amount = token_normalized_value(token_amount=amount_raw, token=token)
        notes = f'Transfer {amount} {token.symbol} {from_address} -> {to_address}'
        return HistoryBaseEntry(
            event_identifier='0x' + transaction.tx_hash.hex(),
            sequence_index=log.log_index,
            timestamp=transaction.timestamp,
            location=Location.BLOCKCHAIN,
            location_label=location_label,
            asset_balance=AssetBalance(asset=token, balance=Balance(amount=amount)),
            notes=notes,
            event_type=event_type,
            event_subtype=None,
            counterparty=counterparty,
        )
