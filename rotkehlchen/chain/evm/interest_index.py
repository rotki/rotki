"""Reserve interest index call builder for EVM balance multicalls.

During EVM token balance queries, index-accruing tokens (Aave v3 and Spark Lend aTokens
and variable debt tokens) need their protocol's current reserve index captured in the exact
same multicall block as ``tokens_balance`` so reconciliation stays 100% DB-only with zero
archive node queries.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rotkehlchen.assets.types import ACCRUING_INTEREST_FLAGS, AssetFlag
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from eth_typing.abi import ABI

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.types import WeightedNode
    from rotkehlchen.types import ChainID, ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

AAVE_V3_LIKE_PROTOCOLS: Final = frozenset((CPT_AAVE_V3, CPT_SPARK))

AAVE_V3_POOL_INDEX_ABI: Final[ABI] = [
    {
        'inputs': [{'name': 'asset', 'type': 'address'}],
        'name': 'getReserveNormalizedIncome',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'name': 'asset', 'type': 'address'}],
        'name': 'getReserveNormalizedVariableDebt',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

AAVE_V3_TOKEN_METADATA_ABI: Final[ABI] = [
    {
        'inputs': [],
        'name': 'POOL',
        'outputs': [{'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'UNDERLYING_ASSET_ADDRESS',
        'outputs': [{'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

_POOL_INDEX_CONTRACT: Final = EvmContract(address=ZERO_ADDRESS, abi=AAVE_V3_POOL_INDEX_ABI)
_TOKEN_META_CONTRACT: Final = EvmContract(address=ZERO_ADDRESS, abi=AAVE_V3_TOKEN_METADATA_ABI)

# Both POOL() and UNDERLYING_ASSET_ADDRESS() are immutable on Aave v3 / Spark token contracts,
# so caching resolved values per (chain_id, token_address) is safe for the process lifetime.
# Failed lookups are never cached.
_POOL_CACHE: dict[tuple[ChainID, ChecksumEvmAddress], ChecksumEvmAddress] = {}
_UNDERLYING_CACHE: dict[tuple[ChainID, ChecksumEvmAddress], ChecksumEvmAddress] = {}


def clear_caches() -> None:
    """Clear cached on-chain token metadata (intended for tests)."""
    _POOL_CACHE.clear()
    _UNDERLYING_CACHE.clear()


def _decode_positive_uint256(raw_output: bytes) -> int | None:
    """Decode a uint256 reserve index output, returning None if malformed or non-positive."""
    try:
        decoded = _POOL_INDEX_CONTRACT.decode(
            result=raw_output,
            method_name='getReserveNormalizedIncome',
            arguments=[ZERO_ADDRESS],
        )[0]
    except (DeserializationError, IndexError) as e:
        log.debug('Failed to decode reserve index output: %s', e)
        return None

    if not isinstance(decoded, int) or decoded <= 0:
        log.debug('Ignoring non-positive reserve index: %r', decoded)
        return None

    return decoded


@dataclass(frozen=True)
class IndexCallBatch:
    """Deduplicated reserve index sub-calls for a multicall and their token mapping."""
    raw_calls: list[tuple[ChecksumEvmAddress, str]]
    token_to_call_idx: dict[EvmToken, int]

    def __bool__(self) -> bool:
        return len(self.raw_calls) != 0

    def decode(self, outputs: Sequence[tuple[bool, bytes]]) -> dict[EvmToken, int]:
        """Decode multicall_2 outputs for this batch into per-token positive ray ints."""
        decoded_by_idx: dict[int, int] = {}
        for idx, ((target, _), (status, raw_output)) in enumerate(
            zip(self.raw_calls, outputs, strict=False),
        ):
            if status is False or len(raw_output) == 0:
                log.debug('Reserve index sub-call failed for pool %s', target)
                continue
            if (index_value := _decode_positive_uint256(raw_output)) is not None:
                decoded_by_idx[idx] = index_value

        return {
            token: index_value
            for token, call_idx in self.token_to_call_idx.items()
            if (index_value := decoded_by_idx.get(call_idx)) is not None
        }


def _resolve_aave_v3_metadata(
        tokens_needing_pool: list[EvmToken],
        tokens_needing_underlying: list[EvmToken],
        evm_inquirer: EvmNodeInquirer,
        call_order: Sequence[WeightedNode] | None,
) -> None:
    """Resolve missing immutable POOL() / UNDERLYING_ASSET_ADDRESS() in one batched multicall."""
    calls: list[tuple[ChecksumEvmAddress, str]] = []
    call_specs: list[tuple[EvmToken, str]] = []
    pool_calldata = _TOKEN_META_CONTRACT.encode(method_name='POOL', arguments=[])
    underlying_calldata = _TOKEN_META_CONTRACT.encode(
        method_name='UNDERLYING_ASSET_ADDRESS',
        arguments=[],
    )
    for token in tokens_needing_pool:
        calls.append((token.evm_address, pool_calldata))
        call_specs.append((token, 'POOL'))
    for token in tokens_needing_underlying:
        calls.append((token.evm_address, underlying_calldata))
        call_specs.append((token, 'UNDERLYING_ASSET_ADDRESS'))

    if len(calls) == 0:
        return

    try:
        outputs = evm_inquirer.multicall_2(
            calls=calls,
            require_success=False,
            call_order=call_order,
        )
    except RemoteError as e:
        log.warning(
            'Failed to resolve Aave v3/Spark token metadata on %s: %s',
            evm_inquirer.chain_name,
            e,
        )
        return

    for (token, method_name), (status, raw_output) in zip(call_specs, outputs, strict=False):
        if status is False or len(raw_output) == 0:
            log.debug(
                'Metadata call %s() failed for %s on %s',
                method_name,
                token.identifier,
                evm_inquirer.chain_name,
            )
            continue

        try:
            resolved_address = _TOKEN_META_CONTRACT.decode(
                result=raw_output,
                method_name=method_name,
                arguments=[],
            )[0]
        except (DeserializationError, IndexError) as e:
            log.debug(
                'Failed to decode %s() for %s on %s: %s',
                method_name,
                token.identifier,
                evm_inquirer.chain_name,
                e,
            )
            continue

        if resolved_address == ZERO_ADDRESS:
            continue

        cache_key = (evm_inquirer.chain_id, token.evm_address)
        if method_name == 'POOL':
            _POOL_CACHE[cache_key] = resolved_address
        else:
            _UNDERLYING_CACHE[cache_key] = resolved_address


def get_accruing_asset_flags() -> dict[str, AssetFlag]:
    """Return a map from asset identifier to its accruing-interest AssetFlag."""
    flag_to_ids = GlobalDBHandler.get_asset_ids_with_flags(ACCRUING_INTEREST_FLAGS)
    accruing_flags: dict[str, AssetFlag] = {}
    for flag in ACCRUING_INTEREST_FLAGS:
        for identifier in flag_to_ids.get(flag, ()):
            accruing_flags[identifier] = flag
    return accruing_flags


def build_interest_index_batch(
        tokens: Sequence[EvmToken],
        accruing_flags: Mapping[str, AssetFlag],
        evm_inquirer: EvmNodeInquirer,
        call_order: Sequence[WeightedNode] | None = None,
) -> IndexCallBatch:
    """Build a deduplicated batch of reserve index sub-calls for any accruing tokens in ``tokens``.

    Non-accruing tokens (and tokens from unsupported protocols) are skipped with zero RPC overhead.
    """
    if len(accruing_flags) == 0:
        return IndexCallBatch(raw_calls=[], token_to_call_idx={})

    unique_tokens: dict[EvmToken, AssetFlag] = {}
    for token in tokens:
        if (
            (flag := accruing_flags.get(token.identifier)) is not None and
            token.protocol in AAVE_V3_LIKE_PROTOCOLS
        ):
            unique_tokens[token] = flag

    if len(unique_tokens) == 0:
        return IndexCallBatch(raw_calls=[], token_to_call_idx={})

    chain_id = evm_inquirer.chain_id
    tokens_needing_pool = [
        token for token in unique_tokens
        if (chain_id, token.evm_address) not in _POOL_CACHE
    ]
    tokens_needing_underlying = [
        token for token in unique_tokens
        if (chain_id, token.evm_address) not in _UNDERLYING_CACHE and
        len(token.underlying_tokens) != 1
    ]
    if len(tokens_needing_pool) != 0 or len(tokens_needing_underlying) != 0:
        _resolve_aave_v3_metadata(
            tokens_needing_pool=tokens_needing_pool,
            tokens_needing_underlying=tokens_needing_underlying,
            evm_inquirer=evm_inquirer,
            call_order=call_order,
        )

    raw_calls: list[tuple[ChecksumEvmAddress, str]] = []
    call_to_idx: dict[tuple[ChecksumEvmAddress, str], int] = {}
    token_to_call_idx: dict[EvmToken, int] = {}

    for token, flag in unique_tokens.items():
        cache_key = (chain_id, token.evm_address)
        pool_address = _POOL_CACHE.get(cache_key)
        underlying_address = _UNDERLYING_CACHE.get(cache_key)
        if underlying_address is None and len(token.underlying_tokens) == 1:
            underlying_address = token.underlying_tokens[0].address

        if pool_address is None or underlying_address is None:
            continue

        method_name = (
            'getReserveNormalizedIncome'
            if flag == AssetFlag.ACCRUING_INTEREST_SUPPLY
            else 'getReserveNormalizedVariableDebt'
        )
        call = (
            pool_address,
            _POOL_INDEX_CONTRACT.encode(
                method_name=method_name,
                arguments=[underlying_address],
            ),
        )
        if (call_idx := call_to_idx.get(call)) is None:
            call_idx = len(raw_calls)
            call_to_idx[call] = call_idx
            raw_calls.append(call)
        token_to_call_idx[token] = call_idx

    return IndexCallBatch(raw_calls=raw_calls, token_to_call_idx=token_to_call_idx)
