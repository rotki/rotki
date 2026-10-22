import json
import logging
import operator
import re
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple, overload

import requests

from rotkehlchen.chain.evm.types import EvmIndexer
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, TimestampLookupUnsupported
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
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
    Timestamp,
    deserialize_evm_tx_hash,
)
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
ENVELOPE: Final = frozenset({'status', 'message', 'result', 'generation'})
# The answers whose refusal names the block the nest's history starts at, to ask again from.
STAKING_ACTIONS: Final = frozenset({
    'txsBeaconWithdrawal',
    'nuthatchProducedBlocks',
    'nuthatchValidatorBlocks',
})
HISTORY_STARTS: Final = re.compile(r'(?:history starts at|proposals are proven from) block (\d+)')
NOT_PROVEN_YET: Final = re.compile(r'proposals are not proven from block \d+ yet')


class HistoryStartsLater(RemoteError):
    """The nest's history, or its proof of proposers, starts after the range asked about."""

    def __init__(self, message: str, first_block: int) -> None:
        super().__init__(message)
        self.first_block = first_block


class NuthatchPage(list):  # noqa: FURB189  # a real list, as the base's callers expect
    """A page of rows, the snapshot the nest cut it from, and the answer's other top-level
    fields."""

    def __init__(
            self,
            rows: list[dict[str, Any]],
            generation: str | None,
            meta: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(rows)
        self.generation = generation
        self.meta = meta or {}


class ValidatorBlocks(NamedTuple):
    """A validator's proposals the nest proved over [from_block, through]: every block it
    proposed there, so an empty list is a proven empty interval."""
    from_block: int
    through: int
    rows: list[dict[str, Any]]


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
                return NuthatchPage(
                    rows=rows,
                    generation=generation if isinstance(generation, str) else None,
                    meta={k: v for k, v in json_ret.items() if k not in ENVELOPE},
                )
            return False

        message = f'{self.name} cannot answer {action} on {chain_id.to_name()}: {result}'
        if (
                action == 'getblocknobytime' and
                str(result).startswith(NUTHATCH_UNSUPPORTED) and
                'chainid' not in str(result)
        ):  # e.g. on a chain whose blocks can share a second
            raise TimestampLookupUnsupported(message)
        if action in STAKING_ACTIONS and (starts := HISTORY_STARTS.search(str(result))) is not None:  # noqa: E501
            raise HistoryStartsLater(message, first_block=int(starts.group(1)))
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

    def finalized_head(self) -> tuple[int, Timestamp]:
        """The Ethereum block the nest's history is final through, and its timestamp. Produced
        blocks are served through it and no further.

        May raise:
        - RemoteError if the nest cannot be reached, or has not read its Ethereum head yet
        """
        with self._one_nest():
            ready = self._nest_call(self._endpoint(), 'GET', '/ready')
            if isinstance(chains := ready.get('chains'), dict):  # a multichain nest
                ready = chains.get(str(ChainID.ETHEREUM.value)) or {}
            if not isinstance(head := ready.get('head'), int):
                raise RemoteError(f'{self.name} has not read its Ethereum head yet')
            return head, self.block_timestamp(head)

    def block_timestamp(self, block_number: int) -> Timestamp:
        """The timestamp of an Ethereum block, as the nest's RPC has it.

        May raise:
        - RemoteError if the nest cannot answer it
        """
        try:
            block = self.get_block_by_number(chain_id=ChainID.ETHEREUM, block_number=block_number, full_transactions=False)  # noqa: E501
        except DeserializationError as e:
            raise RemoteError(f'{self.name} answered block {block_number} with {e!s}') from e
        return Timestamp(block['timestamp'])

    def get_withdrawals(
            self,
            address: ChecksumEvmAddress,
            period: TimestampOrBlockRange,
    ) -> set[int]:
        """Etherscan's withdrawals query and storage, asked of one nest through its head: the
        action and its answer are Etherscan's. A range's end is resolved against the nest's RPC,
        which runs ahead of the blocks the nest has read, so it is cut at the head; the rest is
        the next query's.

        May raise:
        - HistoryStartsLater if the nest's history starts inside the range
        - RemoteError if the nest cannot answer
        - DeserializationError if a row cannot be read
        """
        with self._one_nest():
            head, head_ts = self.finalized_head()
            end = head if period.range_type == 'blocks' else head_ts
            if period.to_value > end:
                if period.from_value > end:
                    return set()
                period = TimestampOrBlockRange(period.range_type, period.from_value, end)
            return Etherscan.get_withdrawals(self, address=address, period=period)  # type: ignore[arg-type]  # only base methods are used

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
        with self._one_nest():
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
                    raise RemoteError(f'Relays disagree about block {conflict.get("blockNumber")} produced by {address}')  # noqa: E501
                blocks.extend(result)
                if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                    return blocks
                options = new_options

    def get_validator_blocks(
            self,
            validator_index: int,
            from_block: int,
            to_block: int | None = None,
    ) -> ValidatorBlocks:
        """Every block `validator_index` proposed from `from_block` through `to_block`, or through
        the last block the nest has proven when `to_block` is None. The nest proves each block's
        proposer from the beacon header its successor commits to, so the answer covers the
        validator, not any address. Every page is read and checked before anything is returned.

        May raise:
        - HistoryStartsLater if the nest's proof of proposers starts after `from_block`
        - RemoteError if the nest cannot prove the interval, or answers rows of another validator
        or pages that do not belong together
        """
        options: dict[str, Any] = {
            'validator': str(validator_index),
            'startblock': str(from_block),
            'sort': 'asc',
            'page': '1',
            'offset': str(self.pagination_limit),
        }
        if to_block is not None:
            options['endblock'] = str(to_block)
        rows: list[dict[str, Any]] = []
        through: int | None = None
        snapshot: tuple[Any, Any] | None = None
        with self._one_nest():
            while True:
                try:
                    result = self._query(
                        chain_id=ChainID.ETHEREUM,
                        module='account',
                        action='nuthatchValidatorBlocks',
                        options=options,
                    )
                except RemoteError as e:
                    # Only an open question can have nothing new for an answer; a range asked
                    # about again that is no longer proven is a refusal, and stays to be asked.
                    if through is None and to_block is None and NOT_PROVEN_YET.search(str(e)) is not None:  # noqa: E501
                        return ValidatorBlocks(from_block=from_block, through=from_block - 1, rows=[])  # noqa: E501
                    raise
                if not isinstance(result, list):
                    raise RemoteError(f'{self.name} answered the blocks of validator {validator_index} with {result}')  # noqa: E501
                meta = getattr(result, 'meta', {})
                try:
                    page_through = int(meta['verifiedThrough'])
                except (KeyError, TypeError, ValueError) as e:
                    raise RemoteError(f'{self.name} did not say how far it proved the blocks of validator {validator_index}') from e  # noqa: E501
                page_snapshot = (getattr(result, 'generation', None), meta.get('supportedFrom'))
                if through is not None and (page_through != through or page_snapshot != snapshot):
                    raise RemoteError(f'{self.name} answered the pages of validator {validator_index} from different proofs')  # noqa: E501
                through, snapshot = page_through, page_snapshot
                for row in result:
                    try:
                        proposer = int(row['proposerIndex'])
                    except (KeyError, TypeError, ValueError) as e:
                        raise RemoteError(f'{self.name} answered a block of validator {validator_index} without its proposer: {row}') from e  # noqa: E501
                    if proposer != validator_index:
                        raise RemoteError(f'{self.name} answered block {row.get("blockNumber")}, proposed by {proposer}, for validator {validator_index}')  # noqa: E501
                rows.extend(result)
                if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                    break
                options = new_options

        if to_block is not None and through < to_block:
            raise RemoteError(f'{self.name} answered the blocks of validator {validator_index} through {to_block} having proved them only through {through}')  # noqa: E501
        # `through` below `from_block` is a nest that has proven nothing new there yet.
        return ValidatorBlocks(
            from_block=from_block,
            through=through if to_block is None else to_block,
            rows=rows,
        )

    def _nest_call(
            self,
            endpoint: str,
            method: Literal['GET', 'POST'],
            path: str,
            body: dict[str, str | int] | None = None,
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
        contacted while no chain's order names it. A removed account stays watched by the nest; a
        removed validator does not.

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
        if ChainID.ETHEREUM in chains:
            self._sync_watched_validators(endpoint, listed)

    def queue_unwatch_validators(self, indices: Sequence[int]) -> None:
        """Remember validators the nest should stop watching, for the next sync to tell it."""
        with self.db.conn.read_ctx() as cursor:
            pending = set(json.loads(self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH_VALIDATORS,
            ) or '[]'))
        pending.update(indices)
        with self.db.user_write() as write_cursor:
            self.db.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH_VALIDATORS,
                value=json.dumps(sorted(pending)),
            )

    def _sync_watched_validators(self, endpoint: str, listed: dict[str, Any]) -> None:
        """Tell the nest to watch every validator rotki tracks, whatever is known of its
        activation or withdrawal address, and to stop watching those rotki removed. `listed` is
        the nest's answer to GET /api/watch.

        May raise:
        - RemoteError if the nest cannot be reached or refuses a change
        """
        try:
            watched = {int(index) for index in listed.get('validators', [])}
        except (TypeError, ValueError) as e:
            raise RemoteError(f'{self.name} listed its watched validators as {listed.get("validators")}') from e  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            tracked = {row[0] for row in cursor.execute('SELECT validator_index FROM eth2_validators WHERE validator_index IS NOT NULL')}  # noqa: E501
            pending = set(json.loads(self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH_VALIDATORS,
            ) or '[]'))
        for index in sorted(tracked - watched):
            self._nest_call(endpoint, 'POST', '/api/watch', {'validator': index})
        for index in sorted(pending):
            if index in watched and index not in tracked:
                self._nest_call(endpoint, 'POST', '/api/unwatch', {'validator': index})
            pending.discard(index)
            with self.db.user_write() as write_cursor:
                self.db.set_static_cache(
                    write_cursor=write_cursor,
                    name=DBCacheStatic.NUTHATCH_PENDING_UNWATCH_VALIDATORS,
                    value=json.dumps(sorted(pending)),
                )

    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """A nest records no L1 fees."""
        raise RemoteError(f'{self.name} does not serve L1 fees')
