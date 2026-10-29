import json
import logging
import operator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, overload

import requests

from rotkehlchen.chain.evm.types import EvmIndexer
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, TimestampLookupUnsupported
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi, HasChainActivity
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_transaction,
    deserialize_int,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.rate_limiter import TokenBucket
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from collections.abc import Iterator

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

NUTHATCH_PAGINATION_LIMIT: Final = 1000
# The nest runs beside rotki, so there is no provider quota to protect, only its own CPU.
NUTHATCH_RATE_LIMIT_RPS: Final = 50.0
NUTHATCH_RATE_LIMIT_BURST: Final = 50
NUTHATCH_UNSUPPORTED: Final = 'NUTHATCH_UNSUPPORTED:'
# Kept in a paged query's options and never sent: the pages it has read so far.
PAGES_READ: Final = '_nuthatch_pages_read'
# The index of an internal row's frame in its transaction's whole trace. The Etherscan-shaped
# traceId only encodes depth, so two value transfers at one depth would share it.
TRACE_INDEX: Final = 'nuthatchTraceIndex'
# The nest every request of the running query goes to. Set by Nuthatch._one_nest.
PINNED_ENDPOINT: Final[ContextVar[str | None]] = ContextVar('nuthatch_endpoint', default=None)


class NuthatchPage(list):  # noqa: FURB189  # a real list, as the base's callers expect
    """A page of rows, and the snapshot the nest cut it from."""

    def __init__(self, rows: list[dict[str, Any]], generation: str | None) -> None:
        super().__init__(rows)
        self.generation = generation


class Nuthatch(EtherscanLikeApi):
    """A nuthatch nest (https://nuthatch-indexer.com) in rotki mode, serving the history of the
    addresses it watches at an Etherscan-shaped `/api`.

    A nest answers only what it has indexed completely. Anything else comes back as
    NUTHATCH_UNSUPPORTED or NUTHATCH_INCOMPLETE, never as an empty list, and is raised here so
    that rotki moves on to the next indexer. For the same reason a row rotki cannot read refuses
    the whole answer instead of being skipped.
    """

    def __init__(
            self,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            indexer_stats: IndexerStats | None = None,
    ) -> None:
        super().__init__(
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
    def _endpoint() -> str:
        if (pinned := PINNED_ENDPOINT.get()) is not None:
            return pinned
        return str(CachedSettings().get_entry('nuthatch_api_endpoint')).rstrip('/')

    @contextmanager
    def _one_nest(self) -> Iterator[None]:
        """Pin the endpoint for every request of one query, so that a changed setting cannot
        put pages of two nests into one answer."""
        token = PINNED_ENDPOINT.set(self._endpoint())
        try:
            yield
        finally:
            PINNED_ENDPOINT.reset(token)

    @staticmethod
    def _get_url(chain_id: SUPPORTED_CHAIN_IDS) -> str:
        return f'{Nuthatch._endpoint()}/api'

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

    def _additional_json_response_handling(
            self,
            action: str,
            chain_id: ChainID,
            response: Response,
            json_ret: dict[str, Any],
            result: str,
            current_backoff: int,
    ) -> int | bool | list | None:
        """Raise on anything the nest could not answer completely. A nest never raises
        ChainNotSupported, which would remove it from the chain: whatever it refuses, including
        another chain, the query falls through to the next indexer.

        May raise:
        - TimestampLookupUnsupported if the nest never resolves timestamps on the chain
        - RemoteError if the nest has not indexed the request, or refused it
        """
        if json_ret.get('status') != '0':
            if isinstance(rows := json_ret.get('result'), list):
                generation = json_ret.get('generation')
                return NuthatchPage(rows, generation if isinstance(generation, str) else None)
            return False

        message = f'{self.name} cannot answer {action} on {chain_id.to_name()}: {result}'
        if (
                action == 'getblocknobytime' and
                str(result).startswith(NUTHATCH_UNSUPPORTED) and
                'chainid' not in str(result)
        ):  # e.g. on a chain whose blocks can share a second
            raise TimestampLookupUnsupported(message)
        if action == 'getLogs' and 'narrower range' in str(result):
            # the wording rotki's get_logs looks for before it halves the block range
            raise RemoteError(f'{message}. Please select a smaller result dataset')

        raise RemoteError(message)

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

    def _rows(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            action: Literal['txlist', 'txlistinternal', 'tokentx'],
            options: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        """Every row of every page the nest answers. A hash's internals come whole, unpaged.

        May raise:
        - RemoteError if the nest cannot answer a page
        """
        if 'txhash' not in options:
            options |= {'page': '1', 'offset': str(self.pagination_limit)}
        while True:
            page = self._query(chain_id=chain_id, module='account', action=action, options=options)
            if not isinstance(page, list):
                raise RemoteError(f'{self.name} answered {action} with {page}')
            yield from page
            if 'txhash' in options or (new_options := self._maybe_paginate(result=page, options=options)) is None:  # noqa: E501
                return
            options = new_options

    @overload
    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
            tx_timestamp: Timestamp | None = None,
    ) -> Iterator[list[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
            tx_timestamp: Timestamp | None = None,
    ) -> Iterator[list[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
            tx_timestamp: Timestamp | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Every transaction or internal transaction of the account or parent hash, as a single
        batch: rotki picks an indexer by its first batch, so a refusal on a later page must
        surface while the next indexer can still be asked.

        The nest lists an internal frame that reverted, or sits under one that did, with isError
        "1", as Etherscan does. rotki keeps neither that flag nor the frame's failure, and only
        checks whether the whole transaction failed, so such a row is dropped. Pages are counted
        on what the nest answered, not on what survives.

        May raise:
        - RemoteError if the nest cannot answer, or answers a row rotki cannot read
        """
        with self._one_nest():
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

            is_internal = action == 'txlistinternal'
            transactions: list[Any] = []
            for entry in self._rows(chain_id=chain_id, action=action, options=options):
                data = entry
                if is_internal:
                    if entry.get('callType') == 'delegatecall' or entry.get('isError') == '1':
                        continue
                    if (trace_index := entry.get(TRACE_INDEX)) is None:
                        raise RemoteError(f'{self.name} answered an internal transaction without {TRACE_INDEX}: {entry}')  # noqa: E501
                    data = entry | {'traceId': trace_index}
                try:
                    tx, _ = deserialize_evm_transaction(  # type: ignore[call-overload]  # any kind
                        data=data,
                        internal=is_internal,
                        chain_id=chain_id,
                        evm_inquirer=None,
                        parent_tx_hash=parent_tx_hash,
                        indexer=self,
                    )
                except (DeserializationError, KeyError) as e:
                    raise RemoteError(f'{self.name} answered a {action} row rotki cannot read: {e!s}') from e  # noqa: E501
                transactions.append(tx)

        yield transactions

    def get_token_transaction_data(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[tuple[EVMTxHash, Timestamp, int]]]:
        """Token transfer data as one batch of ``(tx_hash, timestamp, block_number)``, read
        whole as get_transactions is.

        May raise:
        - RemoteError if the nest cannot answer, or answers a row rotki cannot read
        """
        with self._one_nest():
            options = {'address': str(account), 'sort': 'asc'}
            if from_block is not None:
                options['startblock'] = str(from_block)
            if to_block is not None:
                options['endblock'] = str(to_block)

            tx_data: set[tuple[EVMTxHash, Timestamp, int]] = set()
            for entry in self._rows(chain_id=chain_id, action='tokentx', options=options):
                try:
                    tx_data.add((
                        deserialize_evm_tx_hash(entry['hash']),
                        deserialize_timestamp(entry['timeStamp']),
                        deserialize_int(entry['blockNumber'], location=f'{self.name} tokentx'),
                    ))
                except (DeserializationError, KeyError) as e:
                    raise RemoteError(f'{self.name} answered a tokentx row rotki cannot read: {e!s}') from e  # noqa: E501

        yield sorted(tx_data, key=operator.itemgetter(1))

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        """The base's several queries, all asked of one nest."""
        with self._one_nest():
            return super().has_activity(chain_id=chain_id, account=account)

    def _nest_call(
            self,
            endpoint: str,
            method: Literal['GET', 'POST'],
            path: str,
            body: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """One call to the nest's own management API, outside the Etherscan-shaped `/api`.

        May raise:
        - RemoteError if the nest cannot be reached or refuses the call
        """
        try:
            response = self.session.request(
                method=method,
                url=f'{endpoint}{path}',
                json=body,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'{self.name} {path} failed: {e!s}') from e

        # A nest that has not reached its chain head yet answers /ready with 503, and still says
        # which chains it is on, which is all the watch sync needs.
        if response.status_code != HTTPStatus.OK and not (
            path == '/ready' and response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        ):
            raise RemoteError(f'{self.name} {path} answered {response.status_code}: {response.text}')  # noqa: E501
        try:
            return jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(f'{self.name} {path} answered invalid JSON: {response.text}') from e

    @staticmethod
    def ordered_chains() -> set[ChainID]:
        """The chains whose indexer order names the nest."""
        return {
            chain_id for chain_id in EVM_CHAIN_IDS_WITH_TRANSACTIONS
            if EvmIndexer.NUTHATCH in CachedSettings().get_evm_indexers_order_for_chain(chain_id=chain_id)  # noqa: E501
        }

    def sync_watched(self) -> None:
        """Tell the nest to watch every account rotki tracks on each chain it serves whose
        indexer order names it, comparing against that chain's own watched list. The nest is not
        contacted while no chain's order names it. A removed account stays watched by the nest.

        Runs as a background task after accounts change and at login. A nest that cannot be
        reached is left for the next run; nothing here may stop an account being added.

        May raise:
        - RemoteError if the nest cannot be reached
        """
        if len(ordered := self.ordered_chains()) == 0:
            return

        endpoint = self._endpoint()  # one nest for the whole sync, whatever the setting does
        ready = self._nest_call(endpoint, 'GET', '/ready')  # a multichain nest lists chain_ids
        if not isinstance(served := ready.get('chain_ids'), list):
            served = [ready.get('chain_id')]
        if len(chains := {chain for chain in ordered if chain.value in served}) == 0:
            return

        with self.db.conn.read_ctx() as cursor:
            accounts = self.db.get_blockchain_accounts(cursor)
        listed = self._nest_call(endpoint, 'GET', '/api/watch')
        per_chain = listed.get('chains')  # a multichain nest's "watched" is the union of these
        missing: set[str] = set()
        for chain in chains:
            watched = per_chain.get(str(chain.value), []) if isinstance(per_chain, dict) else listed.get('watched', [])  # noqa: E501
            missing |= (
                {str(a).lower() for a in accounts.get(chain.to_blockchain())} -
                {str(a).lower() for a in watched}
            )
        for address in sorted(missing):
            self._nest_call(endpoint, 'POST', '/api/watch', {'address': address})

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """A nest records no L1 fees."""
        raise RemoteError(f'{self.name} does not serve L1 fees')
