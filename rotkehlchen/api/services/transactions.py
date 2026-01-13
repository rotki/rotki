from __future__ import annotations

import logging
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, cast

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.chain.evm.types import NodeName
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import CPT_GNOSIS_PAY
from rotkehlchen.chain.zksync_lite.constants import ZKL_IDENTIFIER
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import (
    EvmTransactionsNotDecodedFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.api import PremiumApiError
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.errors.misc import AlreadyExists, InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import has_premium_check
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.types import (
    CHAINS_WITH_NODES,
    CHAINS_WITH_TRANSACTION_DECODERS,
    CHAINS_WITH_TRANSACTION_DECODERS_TYPE,
    CHAINS_WITH_TRANSACTIONS,
    CHAINS_WITH_TRANSACTIONS_TYPE,
    CHAINS_WITH_TX_DECODING_TYPE,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
    EVM_CHAINS_WITH_TRANSACTIONS,
    SUPPORTED_EVM_CHAINS_TYPE,
    ExternalService,
    HistoryEventQueryType,
    ListOfBlockchainAddresses,
    Location,
    SupportedBlockchain,
    Timestamp,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from solders.solders import Signature

    from rotkehlchen.assets.asset import CryptoAsset, EvmToken
    from rotkehlchen.chain.accounts import OptionalBlockchainAccount
    from rotkehlchen.chain.evm.types import EvmIndexer, WeightedNode
    from rotkehlchen.chain.manager import ChainManagerWithNodesMixin
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.fval import FVal
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import (
        CHAINS_WITH_NODES_TYPE,
        BlockchainAddress,
        BTCTxId,
        ChecksumEvmAddress,
        EVMTxHash,
        SolanaAddress,
    )

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TransactionsService:
    def __init__(self, rotkehlchen: Rotkehlchen) -> None:
        self.rotkehlchen = rotkehlchen

    def add_transaction_by_reference(
            self,
            blockchain: CHAINS_WITH_TRANSACTIONS_TYPE,
            tx_ref: EVMTxHash | Signature,
            associated_address: ChecksumEvmAddress | SolanaAddress,
    ) -> dict[str, Any]:
        chain_manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)
        try:
            if blockchain == SupportedBlockchain.SOLANA:
                chain_manager.transactions.get_or_create_transaction(  # type: ignore[attr-defined]
                    signature=tx_ref,
                    relevant_address=associated_address,
                )
            else:
                chain_manager.transactions.add_transaction_by_hash(  # type: ignore[attr-defined]
                    tx_hash=tx_ref,
                    associated_address=associated_address,
                )
        except (KeyError, DeserializationError, RemoteError, AlreadyExists, InputError) as e:
            if isinstance(e, AlreadyExists):
                status_code = HTTPStatus.CONFLICT
            elif isinstance(e, InputError):
                status_code = HTTPStatus.NOT_FOUND
            else:
                status_code = HTTPStatus.BAD_GATEWAY

            return {
                'result': None,
                'message': (
                    f'Unable to add transaction with reference {tx_ref!s} for blockchain '
                    f'{blockchain} and associated address {associated_address} due to {e!s}'
                ),
                'status_code': status_code,
            }

        chain_manager.transactions_decoder.decode_transaction_hashes(  # type: ignore[attr-defined]
            ignore_cache=True,
            tx_hashes=[tx_ref],
        )
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def get_rpc_nodes(self, blockchain: SupportedBlockchain) -> dict[str, Any]:
        nodes = self.rotkehlchen.data.db.get_rpc_nodes(blockchain=blockchain)
        return {
            'result': process_result_list(list(nodes)),
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def add_rpc_node(self, node: WeightedNode) -> dict[str, Any]:
        try:
            self.rotkehlchen.data.db.add_rpc_node(node)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def update_and_connect_rpc_node(self, node: WeightedNode) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if (old_endpoint_row := cursor.execute(
                'SELECT endpoint FROM rpc_nodes WHERE identifier=?',
                (node.identifier,),
            ).fetchone()) is None:
                return {
                    'result': None,
                    'message': f"Node with identifier {node.identifier} doesn't exist",
                    'status_code': HTTPStatus.CONFLICT,
                }
            old_endpoint = old_endpoint_row[0]

        try:
            self.rotkehlchen.data.db.update_rpc_node(node)
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        nodes_to_connect = self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=node.node_info.blockchain,
            only_active=True,
        )

        manager = cast(
            'ChainManagerWithNodesMixin',
            self.rotkehlchen.chains_aggregator.get_chain_manager(
                blockchain=node.node_info.blockchain,
            ),
        )
        for entry in list(manager.node_inquirer.rpc_mapping):
            if entry.endpoint == old_endpoint:
                manager.node_inquirer.rpc_mapping.pop(entry, None)
                break
        else:
            log.debug(
                f'Failed to find node with endpoint {old_endpoint} in web3 mappings. Skipping',
            )

        manager.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_rpc_node(self, identifier: int, blockchain: SupportedBlockchain) -> dict[str, Any]:
        try:
            self.rotkehlchen.data.db.delete_rpc_node(
                identifier=identifier,
                blockchain=blockchain,
            )
        except InputError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        nodes_to_connect = self.rotkehlchen.data.db.get_rpc_nodes(
            blockchain=blockchain,
            only_active=True,
        )
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain)  # type: ignore
        manager.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)
        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def connect_rpc_node(
            self,
            identifier: int | None,
            blockchain: SupportedBlockchain,
    ) -> dict[str, Any]:
        if blockchain not in CHAINS_WITH_NODES:
            return {
                'result': None,
                'message': f'{blockchain} nodes are connected at login',
                'status_code': HTTPStatus.BAD_REQUEST,
            }

        bindings: tuple[str | int, ...]
        if identifier is not None:
            query, bindings = (
                'SELECT name, endpoint, owned, blockchain FROM rpc_nodes WHERE identifier=?',
                (identifier,),
            )
        else:
            query, bindings = (
                'SELECT name, endpoint, owned, blockchain FROM rpc_nodes WHERE blockchain=?',
                (blockchain.value,),
            )

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if len(db_entries := cursor.execute(query, bindings).fetchall()) == 0:
                return {
                    'result': None,
                    'message': 'RPC node not found',
                    'status_code': HTTPStatus.BAD_REQUEST,
                }

        blockchain_with_nodes = cast('CHAINS_WITH_NODES_TYPE', blockchain)
        manager = cast(
            'ChainManagerWithNodesMixin',
            self.rotkehlchen.chains_aggregator.get_chain_manager(
                blockchain=blockchain_with_nodes,
            ),
        )
        errors = []
        for row in db_entries:
            success, msg = manager.node_inquirer.attempt_connect(node=(node := NodeName(
                name=row[0],
                endpoint=row[1],
                owned=bool(row[2]),
                blockchain=blockchain_with_nodes,
            )))
            if success is False:
                errors.append({'name': node.name, 'error': msg})

        return {'result': {'errors': errors}, 'message': '', 'status_code': HTTPStatus.OK}

    def get_watchers(self) -> dict[str, Any]:
        return self._watcher_query(method='GET', data=None)

    def add_watchers(self, watchers: list[dict[str, Any]]) -> dict[str, Any]:
        return self._watcher_query(method='PUT', data={'watchers': watchers})

    def edit_watchers(self, watchers: list[dict[str, Any]]) -> dict[str, Any]:
        return self._watcher_query(method='PATCH', data={'watchers': watchers})

    def delete_watchers(self, watchers: list[str]) -> dict[str, Any]:
        return self._watcher_query(method='DELETE', data={'watchers': watchers})

    def _watcher_query(
            self,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            result_json = self.rotkehlchen.premium.watcher_query(  # type:ignore[union-attr]
                method=method,
                data=data,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_GATEWAY}
        except PremiumApiError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {'result': result_json, 'message': '', 'status_code': HTTPStatus.OK}

    def delete_blockchain_transaction_data(
            self,
            chain: CHAINS_WITH_TRANSACTIONS_TYPE | None,
            tx_ref: EVMTxHash | Signature | BTCTxId | None,
    ) -> dict[str, Any]:
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            if tx_ref is not None:
                dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=[tx_ref],
                    location=Location.from_chain(chain),  # type: ignore[arg-type]
                )
            else:
                chains = [chain] if chain is not None else CHAINS_WITH_TRANSACTIONS
                for chain_location in [Location.from_chain(i_chain) for i_chain in chains]:
                    dbevents.reset_events_for_redecode(
                        write_cursor=write_cursor,
                        location=chain_location,
                    )

            if not chain:
                DBEvmTx(self.rotkehlchen.data.db).delete_evm_transaction_data(
                    write_cursor=write_cursor,
                )
                DBSolanaTx(self.rotkehlchen.data.db).delete_transaction_data(
                    write_cursor=write_cursor,
                )
                self._delete_zksync_tx_data(write_cursor=write_cursor)
                for cache_key in (
                    DBCacheDynamic.LAST_BTC_TX_BLOCK,
                    DBCacheDynamic.LAST_BCH_TX_BLOCK,
                ):
                    self._delete_bitcoin_tx_data(write_cursor=write_cursor, cache_key=cache_key)
            elif chain.is_evm():
                DBEvmTx(self.rotkehlchen.data.db).delete_evm_transaction_data(
                    write_cursor=write_cursor,
                    chain=chain,  # type: ignore[arg-type]
                    tx_hash=tx_ref,  # type: ignore[arg-type]
                )
            elif chain == SupportedBlockchain.SOLANA:
                DBSolanaTx(self.rotkehlchen.data.db).delete_transaction_data(
                    write_cursor=write_cursor,
                    signature=tx_ref,  # type: ignore[arg-type]
                )
            elif chain == SupportedBlockchain.ZKSYNC_LITE:
                self._delete_zksync_tx_data(
                    write_cursor=write_cursor,
                    tx_hash=tx_ref,  # type: ignore[arg-type]
                )
            elif chain.is_bitcoin() and tx_ref is None:
                self._delete_bitcoin_tx_data(
                    write_cursor=write_cursor,
                    cache_key=(
                        DBCacheDynamic.LAST_BTC_TX_BLOCK
                        if chain == SupportedBlockchain.BITCOIN
                        else DBCacheDynamic.LAST_BCH_TX_BLOCK
                    ),
                )

        return {'result': True, 'message': '', 'status_code': HTTPStatus.OK}

    def refresh_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            accounts: list[OptionalBlockchainAccount] | None,
    ) -> dict[str, Any]:
        blockchain_addresses: dict[CHAINS_WITH_TRANSACTIONS_TYPE, ListOfBlockchainAddresses]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if accounts is None or len(accounts) == 0:
                blockchain_addresses = {
                    chain: addr_list for chain in CHAINS_WITH_TRANSACTIONS
                    if len(addr_list := self.rotkehlchen.data.db.get_single_blockchain_addresses(
                        cursor=cursor,
                        blockchain=chain,
                    )) != 0
                }
            else:
                blockchain_addresses = defaultdict(list)
                unspecified_chain_addresses: list[BlockchainAddress] = []
                for account in accounts:
                    if account.chain is not None and account.chain in CHAINS_WITH_TRANSACTIONS:
                        blockchain_addresses[account.chain].append(account.address)  # type: ignore
                    else:
                        unspecified_chain_addresses.append(account.address)

                if len(unspecified_chain_addresses) > 0:
                    for address, chain in self.rotkehlchen.data.db.get_blockchains_for_accounts(
                        cursor=cursor,
                        accounts=unspecified_chain_addresses,
                    ):
                        if chain not in CHAINS_WITH_TRANSACTIONS:
                            continue

                        blockchain_addresses[chain].append(address)  # type: ignore

        result, message, status_code = True, '', HTTPStatus.OK
        for blockchain, addresses in blockchain_addresses.items():
            try:
                self.rotkehlchen.chains_aggregator.get_chain_manager(
                    blockchain=blockchain,
                ).query_transactions(
                    addresses=addresses,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                )
            except AttributeError:
                result = False
                message = f'Transaction querying for {blockchain} is not implemented.'
                status_code = HTTPStatus.BAD_REQUEST
                break
            except RemoteError as e:
                result, message, status_code = False, str(e), HTTPStatus.BAD_GATEWAY
                break
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                result, message, status_code = False, str(e), HTTPStatus.BAD_REQUEST
                break

        return {'result': result, 'message': message, 'status_code': status_code}

    def decode_given_transactions(
            self,
            chain: CHAINS_WITH_TX_DECODING_TYPE,
            tx_refs: list[EVMTxHash | Signature],
            delete_custom: bool,
            custom_indexers_order: list[EvmIndexer] | None = None,
    ) -> dict[str, Any]:
        success, message, status_code = True, '', HTTPStatus.OK
        indexer_order_customized = (
            CachedSettings().evm_indexers_order_override_var.set(tuple(custom_indexers_order))
            if custom_indexers_order
            else None
        )
        try:
            if chain.is_evm():
                evm_chain = cast('SUPPORTED_EVM_CHAINS_TYPE', chain)
                evm_tx_refs = cast('list[EVMTxHash]', tx_refs)
                for evm_tx_ref in evm_tx_refs:
                    self._decode_given_evm_tx(
                        chain=evm_chain,
                        tx_ref=evm_tx_ref,
                        delete_custom=delete_custom,
                    )
            elif chain.is_evmlike():
                evmlike_tx_refs = cast('list[EVMTxHash]', tx_refs)
                for evmlike_tx_ref in evmlike_tx_refs:
                    self._decode_given_evmlike_tx(evmlike_tx_ref, delete_custom)
            else:
                solana_tx_refs = cast('list[Signature]', tx_refs)
                for solana_tx_ref in solana_tx_refs:
                    self._decode_given_solana_tx(solana_tx_ref, delete_custom)
        except (RemoteError, DeserializationError, InputError) as e:
            success = False
            message = (
                f'Failed to request {chain.name.lower()} transaction decoding due to {e!s}'
            )
            status_code = (
                HTTPStatus.CONFLICT
                if isinstance(e, InputError)
                else HTTPStatus.BAD_GATEWAY
            )
        finally:
            if indexer_order_customized:
                CachedSettings().evm_indexers_order_override_var.reset(indexer_order_customized)

        return {'result': success, 'message': message, 'status_code': status_code}

    def decode_transactions(
            self,
            chain: CHAINS_WITH_TX_DECODING_TYPE,
            force_redecode: bool,
    ) -> dict[str, Any]:
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)
        dbevents = DBHistoryEvents(self.rotkehlchen.data.db)
        if chain.is_evmlike():
            decoded_count = self.rotkehlchen.chains_aggregator.zksync_lite.decode_undecoded_transactions(  # noqa: E501
                force_redecode=force_redecode,
                send_ws_notifications=True,
            )
        else:
            if force_redecode:
                with self.rotkehlchen.data.db.user_write() as write_cursor:
                    dbevents.reset_events_for_redecode(
                        write_cursor=write_cursor,
                        location=Location.from_chain(chain),
                    )

                if chain == SupportedBlockchain.ETHEREUM:
                    DBEth2(self.rotkehlchen.data.db).redecode_block_production_events()

            chain_manager = self.rotkehlchen.chains_aggregator.get_chain_manager(chain)
            if chain.is_evm():
                chain_manager.transactions.get_receipts_for_transactions_missing_them()  # type: ignore[attr-defined]
                decoded_count = dbevmtx.count_hashes_not_decoded(
                    filter_query=EvmTransactionsNotDecodedFilterQuery.make(
                        chain_id=chain.to_chain_id(),
                    ),
                )
            else:
                decoded_count = DBSolanaTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
                    filter_query=SolanaTransactionsNotDecodedFilterQuery.make(),
                )

            if decoded_count > 0:
                chain_manager.transactions_decoder.get_and_decode_undecoded_transactions(  # type: ignore[attr-defined]
                    send_ws_notifications=True,
                )

        return {'result': {'decoded_tx_number': decoded_count}, 'message': '', 'status_code': HTTPStatus.OK}  # noqa: E501

    def get_evm_transactions_status(self) -> dict[str, Any]:
        where_str = ' OR '.join(['name LIKE ?'] * len(EVM_CHAINS_WITH_TRANSACTIONS))
        bindings = [
            f'{blockchain.to_range_prefix("txs")}_%'
            for blockchain in EVM_CHAINS_WITH_TRANSACTIONS
        ]
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            last_queried_ts = cursor.execute(
                f'SELECT MAX(end_ts) FROM used_query_ranges WHERE {where_str}',
                bindings,
            ).fetchone()[0] or Timestamp(0)
            has_evm_accounts = cursor.execute(
                f'SELECT COUNT(*) FROM blockchain_accounts WHERE blockchain IN ({",".join(["?"] * len(EVM_CHAINS_WITH_TRANSACTIONS))})',  # noqa: E501
                [blockchain.value for blockchain in EVM_CHAINS_WITH_TRANSACTIONS],
            ).fetchone()[0] > 0

        undecoded_count = DBEvmTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
            filter_query=EvmTransactionsNotDecodedFilterQuery.make(),
        )
        return {
            'result': {
                'last_queried_ts': last_queried_ts,
                'undecoded_tx_count': undecoded_count,
                'has_evm_accounts': has_evm_accounts,
            },
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def get_count_transactions_not_decoded(self) -> dict[str, Any]:
        tx_info: dict[str, dict[str, int]] = defaultdict(dict)
        dbevmtx = DBEvmTx(self.rotkehlchen.data.db)

        for chain in EVM_CHAIN_IDS_WITH_TRANSACTIONS:
            if (undecoded_count := dbevmtx.count_hashes_not_decoded(
                filter_query=EvmTransactionsNotDecodedFilterQuery.make(chain_id=chain),
            )) == 0:
                continue

            tx_info[chain_name := chain.name.lower()]['undecoded'] = undecoded_count
            tx_info[chain_name]['total'] = dbevmtx.count_evm_transactions(chain_id=chain)

        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            if (undecoded_count := cursor.execute(
                'SELECT COUNT(*) FROM zksynclite_transactions WHERE is_decoded=0',
            ).fetchone()[0]) != 0:
                tx_info[chain_name := SupportedBlockchain.ZKSYNC_LITE.name.lower()]['undecoded'] = undecoded_count  # noqa: E501
                tx_info[chain_name]['total'] = cursor.execute(
                    'SELECT COUNT(*) FROM zksynclite_transactions',
                ).fetchone()[0]

        if (undecoded_count := DBSolanaTx(self.rotkehlchen.data.db).count_hashes_not_decoded(
            filter_query=SolanaTransactionsNotDecodedFilterQuery.make(),
        )) != 0:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                tx_info[chain_name := SupportedBlockchain.SOLANA.name.lower()]['undecoded'] = undecoded_count  # noqa: E501
                tx_info[chain_name]['total'] = cursor.execute(
                    'SELECT COUNT(*) FROM solana_transactions',
                ).fetchone()[0]

        return {'result': tx_info, 'message': '', 'status_code': HTTPStatus.OK}

    def force_refetch_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            chain: CHAINS_WITH_TRANSACTION_DECODERS_TYPE | None = None,
            address: ChecksumEvmAddress | SolanaAddress | None = None,
    ) -> dict[str, Any]:
        log.debug(
            'Force refetching transactions',
            from_ts=from_timestamp,
            to_ts=to_timestamp,
            chain=chain.name if chain else 'all supported chains',
            address=address or 'all addresses',
        )

        chains_to_query: list[CHAINS_WITH_TRANSACTION_DECODERS_TYPE] = []
        if chain is not None:
            chains_to_query.append(chain)
        else:
            query_str = 'SELECT DISTINCT blockchain FROM blockchain_accounts'
            bindings: list[str] = []
            if address is not None:
                query_str += ' WHERE account=?'
                bindings.append(address)

            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                chains_to_query.extend([
                    blockchain  # type: ignore[misc]  # the check guarantees valid types
                    for row in cursor.execute(query_str, bindings)
                    if (blockchain := SupportedBlockchain.deserialize(row[0])) in CHAINS_WITH_TRANSACTION_DECODERS  # noqa: E501
                ])

        new_transactions: set[tuple[str, str]] = set()
        for query_chain in chains_to_query:
            if query_chain == SupportedBlockchain.SOLANA:
                new_transactions |= self._query_txs_for_range(
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                    address=address,
                    blockchain=SupportedBlockchain.SOLANA,
                    query_for_range_fn=lambda addr, start_ts, end_ts: (
                        self.rotkehlchen.chains_aggregator.solana.transactions.query_transactions_in_range(
                            address=addr,
                            start_ts=start_ts,
                            end_ts=end_ts,
                            return_queried_hashes=True,
                        ) or []
                    ),
                )
            else:
                new_transactions |= self._query_txs_for_range(
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                    address=address,
                    blockchain=query_chain,
                    query_for_range_fn=lambda addr, start_ts, end_ts, qc=query_chain: (
                        self.rotkehlchen.chains_aggregator.get_evm_manager(
                            chain_id=qc.to_chain_id(),
                        ).transactions.refetch_transactions_for_address(
                            address=addr,
                            start_ts=start_ts,
                            end_ts=end_ts,
                            return_queried_hashes=True,
                        ) or []
                    ),
                )

        formatted_new_transactions: defaultdict[str, list[str]] = defaultdict(list)
        for chain_key, tx_hash in new_transactions:
            formatted_new_transactions[chain_key].append(tx_hash)
        new_transactions_count = sum(
            len(tx_hashes) for tx_hashes in formatted_new_transactions.values()
        )
        return {
            'result': {
                'new_transactions': formatted_new_transactions,
                'new_transactions_count': new_transactions_count,
            },
            'message': '',
            'status_code': HTTPStatus.OK,
        }

    def _query_txs_for_range(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            address: ChecksumEvmAddress | SolanaAddress | None,
            blockchain: CHAINS_WITH_TRANSACTION_DECODERS_TYPE,
            query_for_range_fn: (
                Callable[[ChecksumEvmAddress, Timestamp, Timestamp], list[EVMTxHash]] |
                Callable[[SolanaAddress, Timestamp, Timestamp], list[Signature]]
            ),
    ) -> set[tuple[str, str]]:
        if address:
            addresses_to_query: tuple[ChecksumEvmAddress | SolanaAddress, ...] = (address,)
        else:
            with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                addresses_to_query = tuple(
                    self.rotkehlchen.data.db.get_single_blockchain_addresses(
                        cursor=cursor,
                        blockchain=blockchain,
                    ),
                )

        if len(addresses_to_query) == 0:
            return set()

        new_transactions: set[tuple[str, str]] = set()
        chain_key = blockchain.serialize()
        for addr in addresses_to_query:
            try:
                new_hashes = query_for_range_fn(addr, from_timestamp, to_timestamp)  # type: ignore[arg-type]
            except (sqlcipher.OperationalError, RemoteError, DeserializationError) as e:  # pylint: disable=no-member
                log.debug(
                    f'Skipping transaction refetching for {addr} on {blockchain.name.lower()} '
                    f'due to: {e!s}',
                )
                continue
            if len(new_hashes) == 0:
                continue
            new_transactions.update(
                (chain_key, str(tx_hash))
                for tx_hash in new_hashes
            )

        return new_transactions

    def addresses_interacted_before(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM history_events JOIN chain_events_info ON '
                'history_events.identifier=chain_events_info.identifier WHERE '
                'location_label=? AND address=?',
                (from_address, to_address),
            )
            return {
                'result': cursor.fetchone()[0] > 0,
                'message': '',
                'status_code': HTTPStatus.OK,
            }

    def prepare_token_transfer(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            token: EvmToken,
            amount: FVal,
    ) -> dict[str, Any]:
        manager = self.rotkehlchen.chains_aggregator.get_chain_manager(blockchain=blockchain)
        try:
            payload = manager.active_management.create_token_transfer(
                from_address=from_address,
                to_address=to_address,
                token=token,
                amount=amount,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {'result': payload, 'message': '', 'status_code': HTTPStatus.OK}

    def prepare_native_transfer(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
            chain: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            amount: FVal,
    ) -> dict[str, Any]:
        manager = self.rotkehlchen.chains_aggregator.get_evm_manager(chain)
        try:
            payload = manager.active_management.transfer_native_token(
                from_address=from_address,
                to_address=to_address,
                amount=amount,
            )
        except RemoteError as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.BAD_REQUEST}

        return {'result': payload, 'message': '', 'status_code': HTTPStatus.OK}

    def fetch_token_balance_for_address(
            self,
            address: ChecksumEvmAddress,
            evm_chain: EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
            asset: CryptoAsset,
    ) -> dict[str, Any]:
        node_inquirer = self.rotkehlchen.chains_aggregator.get_evm_manager(evm_chain).node_inquirer
        try:
            if asset == node_inquirer.native_token:
                balance = node_inquirer.get_multi_balance([address])[address]
            elif (token := asset.resolve_to_evm_token()).chain_id == evm_chain:
                balance = token_normalized_value(
                    token_amount=node_inquirer.call_contract(
                        contract_address=token.evm_address,
                        abi=node_inquirer.contracts.erc20_abi,
                        method_name='balanceOf',
                        arguments=[address],
                    ),
                    token=token,
                )
            else:
                return {
                    'result': None,
                    'message': 'Token exists on different chain than requested',
                    'status_code': HTTPStatus.CONFLICT,
                }
        except (RemoteError, WrongAssetType, InputError) as e:
            return {'result': None, 'message': str(e), 'status_code': HTTPStatus.CONFLICT}

        return {'result': balance, 'message': '', 'status_code': HTTPStatus.OK}

    def _delete_zksync_tx_data(
            self,
            write_cursor: DBCursor,
            tx_hash: EVMTxHash | None = None,
    ) -> None:
        querystr, bindings = 'DELETE FROM zksynclite_transactions', ()
        if tx_hash is not None:
            querystr += ' WHERE tx_hash=?'
            bindings = (tx_hash,)  # type: ignore

        write_cursor.execute(querystr, bindings)

    def _delete_bitcoin_tx_data(
            self,
            write_cursor: DBCursor,
            cache_key: Literal[DBCacheDynamic.LAST_BTC_TX_BLOCK, DBCacheDynamic.LAST_BCH_TX_BLOCK],
    ) -> None:
        self.rotkehlchen.data.db.delete_dynamic_caches(
            write_cursor=write_cursor,
            key_parts=[cache_key.value[0].removesuffix('{address}')],
        )

    def _decode_given_evm_tx(
            self,
            chain: SUPPORTED_EVM_CHAINS_TYPE,
            tx_ref: EVMTxHash,
            delete_custom: bool,
    ) -> None:
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                (tx_ref, chain.to_chain_id().serialize_for_db()),
            )

        try:
            chain_manager = self.rotkehlchen.chains_aggregator.get_chain_manager(
                blockchain=chain,
            )
            chain_manager.transactions.get_or_query_transaction_receipt(tx_hash=tx_ref)
        except RemoteError as e:
            raise InputError(
                f'hash {tx_ref!s} does not correspond to a transaction at {chain.name}. {e!s}',
            ) from e
        except DeserializationError as e:
            raise InputError(str(e)) from e

        events = chain_manager.transactions_decoder.decode_and_get_transaction_hashes(
            tx_hashes=[tx_ref],
            send_ws_notifications=True,
            ignore_cache=True,
            delete_customized=delete_custom,
        )

        if not has_premium_check(self.rotkehlchen.premium):
            return

        has_gnosis_pay, has_monerium = False, False
        for event in events:
            if chain == SupportedBlockchain.GNOSIS and event.counterparty == CPT_GNOSIS_PAY:
                has_gnosis_pay = True
                break
            elif event.counterparty == CPT_MONERIUM:
                has_monerium = True
                break
        else:
            return

        if (
            has_gnosis_pay and
            self.rotkehlchen.data.db.get_external_service_credentials(
                service_name=ExternalService.GNOSIS_PAY,
            ) is None
        ):
            self.rotkehlchen.msg_aggregator.add_message(
                message_type=WSMessageType.MISSING_API_KEY,
                data={'service': HistoryEventQueryType.GNOSIS_PAY.serialize()},
            )
        elif has_monerium and init_monerium(self.rotkehlchen.data.db) is None:
            self.rotkehlchen.msg_aggregator.add_message(
                message_type=WSMessageType.MISSING_API_KEY,
                data={'service': HistoryEventQueryType.MONERIUM.serialize()},
            )

    def _decode_given_evmlike_tx(self, tx_ref: EVMTxHash, delete_custom: bool) -> None:
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            concerning_address = write_cursor.execute(
                'DELETE FROM zksynclite_transactions WHERE tx_hash=? RETURNING from_address',
                (tx_ref,),
            ).fetchone()
            deleted_event_data = write_cursor.execute(
                'DELETE FROM history_events WHERE group_identifier=? RETURNING location_label',
                (ZKL_IDENTIFIER.format(tx_hash=str(tx_ref)),),
            ).fetchone()
            if deleted_event_data is not None:
                concerning_address = deleted_event_data[0]

        if (transaction := self.rotkehlchen.chains_aggregator.zksync_lite.query_single_transaction(
            tx_hash=tx_ref,
            concerning_address=concerning_address,
        )) is None:
            raise RemoteError(
                f'Failed to fetch transaction {tx_ref!s} from the zksync lite API',
            )

        self.rotkehlchen.chains_aggregator.zksync_lite.decode_transaction(
            transaction=transaction,
            tracked_addresses=self.rotkehlchen.chains_aggregator.accounts.zksync_lite,
        )

    def _decode_given_solana_tx(self, tx_ref: Signature, delete_custom: bool) -> None:
        with self.rotkehlchen.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM solana_transactions WHERE signature=?',
                (tx_ref.to_bytes(),),
            )

        self.rotkehlchen.chains_aggregator.solana.transactions_decoder.decode_and_get_transaction_hashes(
            tx_hashes=[tx_ref],
            send_ws_notifications=True,
            ignore_cache=True,
            delete_customized=delete_custom,
        )
