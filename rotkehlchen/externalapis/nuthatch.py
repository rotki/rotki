import json
import logging
from contextlib import suppress
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.chain.evm.types import EvmIndexer
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import ChainNotSupported, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import EtherscanAccountHistory
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_transaction
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    Location,
)
from rotkehlchen.user_messages import BadData
from rotkehlchen.utils.rate_limiter import TokenBucket
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from requests import Response

    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.indexer_stats import IndexerStats
    from rotkehlchen.types import (
        ChecksumEvmAddress,
        EvmInternalTransaction,
        EvmTransaction,
        EVMTxHash,
        Timestamp,
    )
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# A nest answers at most this many rows a page, as Etherscan does.
NUTHATCH_PAGINATION_LIMIT: Final = 1000
# The nest runs beside rotki, so there is no provider quota to protect, only its own CPU.
NUTHATCH_RATE_LIMIT_RPS: Final = 50.0
NUTHATCH_RATE_LIMIT_BURST: Final = 50
NUTHATCH_UNSUPPORTED: Final = 'NUTHATCH_UNSUPPORTED:'
NUTHATCH_INCOMPLETE: Final = 'NUTHATCH_INCOMPLETE:'
NUTHATCH_PAGED_ACTIONS: Final = frozenset({
    'txlist',
    'txlistinternal',
    'tokentx',
    'txsBeaconWithdrawal',
    'getminedblocks',
})
# Kept in a paged query's options and never sent: the pages it has read so far.
PAGES_READ: Final = '_nuthatch_pages_read'
# The index of an internal row's frame in its transaction's whole trace. The Etherscan-shaped
# traceId only encodes depth, so two value transfers at one depth would share it.
TRACE_INDEX: Final = 'nuthatchTraceIndex'


class NuthatchPage(list):  # noqa: FURB189  # a real list, as the base's callers expect
    """A page of rows, and the snapshot the nest cut it from."""

    def __init__(self, rows: list[dict[str, Any]], generation: str | None) -> None:
        super().__init__(rows)
        self.generation = generation


class Nuthatch(EtherscanAccountHistory):
    """A nuthatch nest (https://nuthatch-indexer.com) in rotki mode, serving the account history
    of the addresses it watches at an Etherscan-shaped `/api`.

    A nest answers only what it has indexed completely. Anything else comes back as
    NUTHATCH_UNSUPPORTED or NUTHATCH_INCOMPLETE, never as an empty list, and is raised here as a
    RemoteError so that rotki moves on to the next indexer.
    """

    def __init__(
            self,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            indexer_stats: IndexerStats | None = None,
    ) -> None:
        EtherscanAccountHistory.__init__(
            self,
            database=database,
            msg_aggregator=msg_aggregator,
            name='Nuthatch',
            pagination_limit=NUTHATCH_PAGINATION_LIMIT,
            default_api_key=ApiKey('none'),
            rate_limiter=TokenBucket(
                rps=NUTHATCH_RATE_LIMIT_RPS,
                capacity=NUTHATCH_RATE_LIMIT_BURST,
            ),
            indexer_stats=indexer_stats,
        )

    @staticmethod
    def _get_url(chain_id: SUPPORTED_CHAIN_IDS) -> str:
        if (endpoint := CachedSettings().get_entry('nuthatch_api_endpoint')) == '':
            raise RemoteError('No nuthatch endpoint is configured')

        return f'{str(endpoint).rstrip("/")}/api'

    def _get_api_key_for_chain(self, chain_id: ChainID) -> ApiKey | None:
        """A nest takes no API key."""
        return None

    @staticmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        return {'module': module, 'action': action, 'chainid': str(chain_id.serialize())}

    def _get_account_pagination_options(
            self,
            action: str,
            options: dict[str, Any],
    ) -> dict[str, str] | None:
        if action in NUTHATCH_PAGED_ACTIONS:
            return {'page': '1', 'offset': str(self.pagination_limit)}
        return None

    def _additional_json_response_handling(
            self,
            action: str,
            chain_id: ChainID,
            response: Response,
            json_ret: dict[str, Any],
            result: str,
            current_backoff: int,
    ) -> int | bool | list | None:
        """Raise on anything the nest could not answer completely.

        May raise:
        - ChainNotSupported if the nest indexes another chain
        - RemoteError if the nest has not indexed the request, or refused it
        """
        if json_ret.get('status') != '0':
            if isinstance(rows := json_ret.get('result'), list):
                generation = json_ret.get('generation')
                return NuthatchPage(rows, generation if isinstance(generation, str) else None)
            return False

        message = str(result)
        if message.startswith(NUTHATCH_UNSUPPORTED) and 'chainid' in message:
            raise ChainNotSupported(f'{self.name} {message}')

        raise RemoteError(f'{self.name} cannot answer {action} on {chain_id.to_name()}: {message}')

    def _query(  # type: ignore[override]  # the overloads are the base's, unchanged
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | str | int | dict[str, Any] | None:
        """The base query, without the paging state a query's options carry."""
        if options is not None and PAGES_READ in options:
            options = {k: v for k, v in options.items() if k != PAGES_READ}
        return super()._query(  # type: ignore[call-overload]  # action is any of the base's
            chain_id=chain_id,
            module=module,
            action=action,
            options=options,
            timeout=timeout,
        )

    def _maybe_paginate(
            self,
            result: list[dict[str, Any]],
            options: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Page with fixed bounds and an incrementing page over the snapshot page 1 was cut from.

        The inherited restart at the last block cannot move past a single block holding a full
        page, so it is not used here. A nest that answers a page it has already answered is an
        error rather than a loop.

        May raise:
        - RemoteError if the nest answered a page it had already answered
        """
        if len(result) < int(options.get('offset', self.pagination_limit)):
            return None

        page = json.dumps(result, sort_keys=True)
        if page in (read := options.setdefault(PAGES_READ, set())):
            raise RemoteError(f'{self.name} answered page {options.get("page")} as an earlier one')

        read.add(page)
        if (generation := getattr(result, 'generation', None)) is not None:
            options.setdefault('generation', generation)
        number = 1
        with suppress(TypeError, ValueError):
            number = int(options.get('page', 1))
        options['page'] = str(number + 1)
        return options

    def get_transactions(  # type: ignore[override]  # same overloads as the base
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
            tx_timestamp: Timestamp | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Every page is read before the first batch is yielded: rotki picks an indexer by its
        first batch, so a refusal on a later page must surface while the next indexer can still be
        asked."""
        if action == 'txlist':
            yield from list(super().get_transactions(
                chain_id=chain_id,
                account=account,
                action='txlist',
                period_or_hash=period_or_hash,
                tx_timestamp=tx_timestamp,
            ))
        else:
            yield self._internal_transactions(
                chain_id=chain_id,
                account=account,
                period_or_hash=period_or_hash,
            )

    def _internal_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None,
    ) -> list[EvmInternalTransaction]:
        """Every internal transaction of the account or parent hash that moved value.

        The nest lists a frame that reverted, or sits under one that did, with isError "1", as
        Etherscan does. rotki keeps neither that flag nor the frame's failure, and only checks
        whether the whole transaction failed, so such a row is dropped here. Pages are counted
        on what the nest answered, not on what survives, or a page of reverted frames would end
        the query early.

        May raise:
        - RemoteError if the nest cannot answer, or a row lacks its trace index
        """
        options: dict[str, Any] = {'sort': 'asc'}
        parent_tx_hash = None
        if account is not None:
            options['address'] = str(account)
        if isinstance(period_or_hash, TimestampOrBlockRange):
            options = self._process_timestamp_or_blockrange(
                chain_id=chain_id,
                period=period_or_hash,
                options=options,
            )
        elif period_or_hash is not None:
            options['txhash'] = period_or_hash.hex()
            parent_tx_hash = period_or_hash
        options.update({'page': '1', 'offset': str(self.pagination_limit)})

        internals: list[EvmInternalTransaction] = []
        while True:
            page = self._query(
                chain_id=chain_id,
                module='account',
                action='txlistinternal',
                options=options,
            )
            if not isinstance(page, list):
                raise RemoteError(f'{self.name} answered internal transactions with {page}')
            for entry in page:
                if entry.get('callType') == 'delegatecall' or entry.get('isError') == '1':
                    continue
                if (trace_index := entry.get(TRACE_INDEX)) is None:
                    raise RemoteError(f'{self.name} answered an internal transaction without {TRACE_INDEX}: {entry}')  # noqa: E501
                try:
                    tx, _ = deserialize_evm_transaction(
                        data=entry | {'traceId': trace_index},
                        internal=True,
                        chain_id=chain_id,
                        evm_inquirer=None,
                        parent_tx_hash=parent_tx_hash,
                        indexer=self,
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(
                        f'{e!s}. Skipping internal transaction {entry.get("hash")} on {chain_id.to_name()} for {account}',  # noqa: E501
                        classification=BadData(record=UserMessageRecord.TRANSACTION, error=str(e)),
                        subject=Location.from_chain_id(chain_id),
                    )
                    continue
                internals.append(tx)

            if (new_options := self._maybe_paginate(result=page, options=options)) is None:
                break
            options = new_options

        return internals

    def get_token_transaction_data(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[tuple[EVMTxHash, Timestamp, int]]]:
        """Read whole before yielding, as get_transactions is."""
        yield from list(super().get_token_transaction_data(
            chain_id=chain_id,
            account=account,
            from_block=from_block,
            to_block=to_block,
        ))

    def get_validated_blocks(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> list[dict[str, Any]]:
        """The blocks `address` produced over `period`: those it was the fee recipient of, and the
        relay-built ones whose builder paid it, each with the relays' record (nuthatch's
        `nuthatchProducedBlocks`, a superset of Etherscan's `getminedblocks`).

        May raise:
        - RemoteError if the nest cannot answer the range, or relays disagree about a block
        """
        options = self._process_timestamp_or_blockrange(
            chain_id=ChainID.ETHEREUM,
            period=period,
            options={'sort': 'asc', 'address': address},
        )
        options.update({'page': '1', 'offset': str(self.pagination_limit)})
        blocks: list[dict[str, Any]] = []
        while True:
            result = self._query(
                chain_id=ChainID.ETHEREUM,
                module='account',
                action='nuthatchProducedBlocks',
                options=options,
            )
            if not isinstance(result, list):
                raise RemoteError(f'{self.name} answered produced blocks with {result}')
            if (conflict := next((r for r in result if r.get('mev') == 'conflict'), None)) is not None:  # noqa: E501
                raise RemoteError(
                    f'Relays disagree about block {conflict.get("blockNumber")} produced by {address}',  # noqa: E501
                )
            blocks.extend(result)
            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break
            options = new_options

        return blocks

    def _nest_call(self, method: Literal['GET', 'POST'], path: str, body: dict[str, str] | None = None) -> dict[str, Any]:  # noqa: E501
        """One call to the nest's own management API, outside the Etherscan-shaped `/api`.

        May raise:
        - RemoteError if the nest cannot be reached or refuses the call
        """
        url = f'{str(CachedSettings().get_entry("nuthatch_api_endpoint")).rstrip("/")}{path}'
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=body,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'{self.name} {path} failed: {e!s}') from e

        # A nest that has not reached its chain head yet answers /ready with 503, and still says
        # which chain it is on, which is all the watch sync needs to tell it what to watch.
        if response.status_code != HTTPStatus.OK and not (
            path == '/ready' and response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        ):
            raise RemoteError(f'{self.name} {path} answered {response.status_code}: {response.text}')  # noqa: E501
        try:
            return jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(f'{self.name} {path} answered invalid JSON: {response.text}') from e

    def queue_unwatch(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """Remember accounts the nest should stop watching, for the next sync to tell it."""
        with self.db.conn.read_ctx() as cursor:
            pending = set(json.loads(self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH,
            ) or '[]'))
        pending.update(str(a) for a in addresses)
        with self.db.user_write() as write_cursor:
            self.db.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH,
                value=json.dumps(sorted(pending)),
            )

    def sync_watched(self) -> None:
        """Tell the nest which accounts to watch: every account rotki tracks on the nest's chain,
        when that chain's indexer order names the nest, and none of those rotki has removed.

        Runs as a background task after accounts change and at login. A nest that cannot be
        reached is left for the next run; nothing here may stop an account being added.

        May raise:
        - RemoteError if the nest cannot be reached
        """
        chain_id = self._nest_call('GET', '/ready').get('chain_id')
        if not isinstance(chain_id, int) or chain_id not in {x.value for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS}:  # noqa: E501
            return

        chain = ChainID.deserialize_from_db(chain_id)
        if EvmIndexer.NUTHATCH not in CachedSettings().get_evm_indexers_order_for_chain(chain_id=chain):  # noqa: E501
            return

        with self.db.conn.read_ctx() as cursor:
            tracked = {str(a).lower() for a in self.db.get_blockchain_accounts(cursor).get(chain.to_blockchain())}  # noqa: E501
            pending = set(json.loads(self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH,
            ) or '[]'))
        watched = {str(a).lower() for a in self._nest_call('GET', '/api/watch').get('watched', [])}
        for address in sorted(tracked - watched):
            self._nest_call('POST', '/api/watch', {'address': address})
        for address in sorted(pending):
            if address.lower() in watched and address.lower() not in tracked:
                self._nest_call('POST', '/api/unwatch', {'address': address})
            pending.discard(address)
            with self.db.user_write() as write_cursor:
                self.db.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH,
                    value=json.dumps(sorted(pending)),
                )

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """A nest records no L1 fees yet."""
        raise RemoteError(f'{self.name} does not serve L1 fees')
