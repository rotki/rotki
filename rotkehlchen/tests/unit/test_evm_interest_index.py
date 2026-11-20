"""Unit tests for EVM reserve interest index capture in EvmTokens."""

from typing import Final
from unittest.mock import MagicMock, patch

import pytest
from eth_abi import encode as abi_encode

from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.assets.types import AssetFlag
from rotkehlchen.chain.ethereum.tokens import EthereumTokens
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.aave.v3.constants import POOL_ADDRESS
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.interest_index import (
    build_interest_index_batch,
    clear_caches,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_USDC, A_WETH
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError, RequestTooLargeError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.observations import (
    ObservationSource,
    get_wallet_observations,
)
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain, TokenKind

pytestmark = [
    pytest.mark.accounting_update,
    pytest.mark.parametrize('use_clean_caching_directory', [True]),
    pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDR1, TEST_ADDR2]]),
]

LIDO_POOL: Final = string_to_evm_address('0x4e033931ad43597d96D6bcc25c280717730B58B1')
SPARK_ETH_POOL: Final = string_to_evm_address('0xC13e21B648A5Ee794902342038FF3aDAB66BE987')

RAY_SUPPLY: Final = 1_051_234_567_890_123_456_789_012_345
RAY_DEBT: Final = 1_089_876_543_210_987_654_321_098_765
RAY_LIDO: Final = 1_033_000_000_000_000_000_000_000_000


def _encode_uint256(value: int) -> bytes:
    return abi_encode(['uint256'], [value])


def _encode_address(address: ChecksumEvmAddress) -> bytes:
    return abi_encode(['address'], [address])


def _encode_tokens_balance(amounts: list[int]) -> bytes:
    return abi_encode(['uint256[]'], [amounts])


def _create_token(
        *,
        symbol: str,
        name: str,
        chain_id: ChainID = ChainID.ETHEREUM,
        decimals: int = 6,
        protocol: str | None = CPT_AAVE_V3,
        underlying: ChecksumEvmAddress | None = None,
        flag: AssetFlag | None = None,
) -> EvmToken:
    address = make_evm_address()
    underlying_tokens = (
        (UnderlyingToken(address=underlying, token_kind=TokenKind.ERC20, weight=FVal(1)),)
        if underlying is not None else ()
    )
    token = EvmToken.initialize(
        address=address,
        chain_id=chain_id,
        token_kind=TokenKind.ERC20,
        decimals=decimals,
        name=name,
        symbol=symbol,
        protocol=protocol,
        underlying_tokens=underlying_tokens,
    )
    GlobalDBHandler.add_asset(token)
    if flag is not None:
        GlobalDBHandler.set_asset_flag(token.identifier, flag, enabled=True)
    return token


@pytest.fixture(autouse=True)
def _clear_index_builder_caches():
    clear_caches()
    yield
    clear_caches()


@pytest.fixture(name='tokens')
def fixture_ethereum_tokens(ethereum_inquirer, database, inquirer):  # pylint: disable=unused-argument
    return EthereumTokens(database, ethereum_inquirer)


def test_build_interest_index_batch_caches_pool_and_decodes_outputs(ethereum_inquirer) -> None:
    """POOL() is resolved once via batched multicall_2 and cached; non-accruing tokens are
    skipped and non-positive or malformed outputs are filtered during decode."""
    sp_dai = _create_token(
        symbol='spDAI',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    sp_debt = _create_token(
        symbol='variableDebtSparkDAI',
        name='Spark Variable Debt DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_DEBT,
    )
    # Spark Savings ERC-4626 token has protocol='spark' but NO accruing flag -> ignored.
    sdai = _create_token(
        symbol='sDAI_test',
        name='Savings DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=None,
    )
    accruing_flags = {
        sp_dai.identifier: AssetFlag.ACCRUING_INTEREST_SUPPLY,
        sp_debt.identifier: AssetFlag.ACCRUING_INTEREST_DEBT,
    }

    with patch.object(
        ethereum_inquirer,
        'multicall_2',
        return_value=[
            (True, _encode_address(SPARK_ETH_POOL)),
            (True, _encode_address(SPARK_ETH_POOL)),
        ],
    ) as mock_multicall_2:
        batch = build_interest_index_batch(
            tokens=[sp_dai, sp_debt, sdai],
            accruing_flags=accruing_flags,
            evm_inquirer=ethereum_inquirer,
        )

    assert mock_multicall_2.call_count == 1
    # Only POOL() calls for sp_dai and sp_debt (underlying_tokens already present, sdai ignored).
    assert len(mock_multicall_2.call_args.kwargs['calls']) == 2
    assert set(batch.token_to_call_idx.keys()) == {sp_dai, sp_debt}
    supply_call = batch.raw_calls[batch.token_to_call_idx[sp_dai]]
    debt_call = batch.raw_calls[batch.token_to_call_idx[sp_debt]]
    assert supply_call[0] == SPARK_ETH_POOL
    assert supply_call[1].startswith('0xd15e0053')  # getReserveNormalizedIncome
    assert debt_call[0] == SPARK_ETH_POOL
    assert debt_call[1].startswith('0x386497fd')  # getReserveNormalizedVariableDebt

    assert batch.decode([
        (True, _encode_uint256(RAY_SUPPLY)),
        (True, _encode_uint256(RAY_DEBT)),
    ]) == {sp_dai: RAY_SUPPLY, sp_debt: RAY_DEBT}
    # Zero and malformed outputs are filtered out.
    assert batch.decode([
        (True, _encode_uint256(0)),
        (True, b'\x01'),
    ]) == {}

    # Second call hits cached POOL() with zero RPC calls.
    with patch.object(ethereum_inquirer, 'multicall_2') as mock_cached:
        cached_batch = build_interest_index_batch(
            tokens=[sp_dai, sp_debt, sdai],
            accruing_flags=accruing_flags,
            evm_inquirer=ethereum_inquirer,
        )
    mock_cached.assert_not_called()
    assert cached_batch == batch


def test_ethereum_multi_pool_and_missing_underlying_cached_on_chain(ethereum_inquirer) -> None:
    """Ethereum Aave v3 resolves exact POOL() (Core vs Lido) and missing UNDERLYING_ASSET_ADDRESS()
    once via batched multicall_2, caches successes, and does not cache failures."""
    weth_addr = A_WETH.resolve_to_evm_token().evm_address
    usdc_addr = A_USDC.resolve_to_evm_token().evm_address
    a_core_weth = _create_token(
        symbol='aEthWETH_test',
        name='Aave Core WETH',
        decimals=18,
        protocol=CPT_AAVE_V3,
        underlying=weth_addr,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    a_lido_weth = _create_token(
        symbol='aEthLidoWETH_test',
        name='Aave Lido WETH',
        decimals=18,
        protocol=CPT_AAVE_V3,
        underlying=weth_addr,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    a_no_underlying = _create_token(
        symbol='aEthNoUnderlying_test',
        name='Aave No Underlying',
        decimals=6,
        protocol=CPT_AAVE_V3,
        underlying=None,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    accruing_flags = {
        a_core_weth.identifier: AssetFlag.ACCRUING_INTEREST_SUPPLY,
        a_lido_weth.identifier: AssetFlag.ACCRUING_INTEREST_SUPPLY,
        a_no_underlying.identifier: AssetFlag.ACCRUING_INTEREST_SUPPLY,
    }

    # First call: Core WETH & Lido WETH succeed, no_underlying fails POOL() -> not cached.
    with patch.object(
        ethereum_inquirer,
        'multicall_2',
        return_value=[
            (True, _encode_address(POOL_ADDRESS)),     # POOL() for a_core_weth
            (True, _encode_address(LIDO_POOL)),        # POOL() for a_lido_weth
            (False, b''),                              # POOL() failed for a_no_underlying
            (True, _encode_address(usdc_addr)),        # UNDERLYING_ASSET_ADDRESS() for a_no_underlying  # noqa: E501
        ],
    ) as mock_meta:
        batch = build_interest_index_batch(
            tokens=[a_core_weth, a_lido_weth, a_no_underlying],
            accruing_flags=accruing_flags,
            evm_inquirer=ethereum_inquirer,
        )

    assert mock_meta.call_count == 1
    assert set(batch.token_to_call_idx.keys()) == {a_core_weth, a_lido_weth}
    assert batch.raw_calls[batch.token_to_call_idx[a_core_weth]][0] == POOL_ADDRESS
    assert batch.raw_calls[batch.token_to_call_idx[a_lido_weth]][0] == LIDO_POOL
    assert batch.token_to_call_idx[a_core_weth] != batch.token_to_call_idx[a_lido_weth]

    # Second call: Core & Lido hit cache (not queried again); only a_no_underlying retries POOL().
    with patch.object(
        ethereum_inquirer,
        'multicall_2',
        return_value=[(True, _encode_address(POOL_ADDRESS))],
    ) as mock_meta_retry:
        batch_retry = build_interest_index_batch(
            tokens=[a_core_weth, a_lido_weth, a_no_underlying],
            accruing_flags=accruing_flags,
            evm_inquirer=ethereum_inquirer,
        )

    assert mock_meta_retry.call_count == 1
    assert len(mock_meta_retry.call_args.kwargs['calls']) == 1  # only POOL() for a_no_underlying
    assert set(batch_retry.token_to_call_idx.keys()) == {
        a_core_weth,
        a_lido_weth,
        a_no_underlying,
    }
    assert batch_retry.raw_calls[batch_retry.token_to_call_idx[a_no_underlying]][0] == POOL_ADDRESS

    # Third call: everything is cached -> zero RPC calls!
    with patch.object(ethereum_inquirer, 'multicall_2') as mock_meta_cached:
        build_interest_index_batch(
            tokens=[a_core_weth, a_lido_weth, a_no_underlying],
            accruing_flags=accruing_flags,
            evm_inquirer=ethereum_inquirer,
        )
    mock_meta_cached.assert_not_called()


def test_query_tokens_non_accruing_chunk_uses_standard_multicall(tokens, database) -> None:
    """Non-accruing tokens make zero extra index calls and keep the standard multicall path."""
    dai = A_DAI.resolve_to_evm_token()
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[dai],
        )

    with (
        patch.object(
            tokens.evm_inquirer,
            'multicall',
            return_value=[_encode_tokens_balance([5 * 10**18])],
        ) as mock_multicall,
        patch.object(tokens.evm_inquirer, 'multicall_2') as mock_multicall_2,
        patch('rotkehlchen.chain.evm.tokens.Inquirer.find_main_currency_prices', return_value={}),
    ):
        balances, _ = tokens.query_tokens_for_addresses([TEST_ADDR1])

    assert mock_multicall.call_count == 1
    mock_multicall_2.assert_not_called()
    assert balances == {TEST_ADDR1: {dai: FVal(5)}}
    obs = get_wallet_observations(database)[LOCATION_ETHEREUM, TEST_ADDR1, dai.identifier]
    assert obs.amount == FVal(5)
    assert obs.observation_index is None


def test_query_tokens_accruing_chunk_atomic_and_deduplicated(tokens, database) -> None:
    """Accruing tokens share deduplicated reserve index sub-calls in one atomic multicall_2."""
    dai_addr = A_DAI.resolve_to_evm_token().evm_address
    sp_dai = _create_token(
        symbol='spDAI_atomic',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=dai_addr,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    sp_debt = _create_token(
        symbol='variableDebtSparkDAI_atomic',
        name='Spark Variable Debt DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=dai_addr,
        flag=AssetFlag.ACCRUING_INTEREST_DEBT,
    )
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[sp_dai, sp_debt],
        )
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR2,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[sp_dai],
        )

    # Determine the exact DB order returned by get_tokens_for_address so mock outputs align.
    with database.conn.read_ctx() as cursor:
        saved_addr1, _ = database.get_tokens_for_address(
            cursor=cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            token_exceptions=set(),
        )
    assert saved_addr1 is not None
    expected_addr1_raw = [10 * 10**18 if t == sp_dai else 3 * 10**18 for t in saved_addr1]
    expected_index_outputs = [
        (True, _encode_uint256(RAY_SUPPLY if t == sp_dai else RAY_DEBT))
        for t in saved_addr1
    ]

    # 1st multicall_2: POOL() metadata for 2 unique tokens.
    # 2nd multicall_2: 2 balance calls (TEST_ADDR1, TEST_ADDR2) + 2 deduplicated index calls = 4.
    # TEST_ADDR2 holds 0 sp_dai — its certified zero still records the same-block index.
    with (
        patch.object(tokens.evm_inquirer, 'multicall') as mock_multicall,
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL)), (True, _encode_address(SPARK_ETH_POOL))],
                [
                    (True, _encode_tokens_balance(expected_addr1_raw)),
                    (True, _encode_tokens_balance([0])),
                    *expected_index_outputs,
                ],
            ],
        ) as mock_multicall_2,
        patch('rotkehlchen.chain.evm.tokens.Inquirer.find_main_currency_prices', return_value={}),
    ):
        balances, _ = tokens.query_tokens_for_addresses([TEST_ADDR1, TEST_ADDR2])

    mock_multicall.assert_not_called()
    assert mock_multicall_2.call_count == 2
    assert len(mock_multicall_2.call_args_list[0].kwargs['calls']) == 2
    assert mock_multicall_2.call_args_list[1].kwargs['require_success'] is False
    assert len(mock_multicall_2.call_args_list[1].kwargs['calls']) == 4

    assert balances == {TEST_ADDR1: {sp_dai: FVal(10), sp_debt: FVal(3)}}
    observations = get_wallet_observations(database)
    obs1_supply = observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier]
    obs1_debt = observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_debt.identifier]
    obs2_supply = observations[LOCATION_ETHEREUM, TEST_ADDR2, sp_dai.identifier]
    assert obs1_supply.amount == FVal(10)
    assert obs1_supply.observation_index == RAY_SUPPLY
    assert obs1_debt.amount == FVal(3)
    assert obs1_debt.observation_index == RAY_DEBT
    assert obs2_supply.amount == ZERO
    assert obs2_supply.observation_index == RAY_SUPPLY


def test_query_tokens_partial_index_failure_preserves_balances(tokens, database) -> None:
    """If a reserve index sub-call reverts or returns 0, balances succeed and observation_index is None."""  # noqa: E501
    dai_addr = A_DAI.resolve_to_evm_token().evm_address
    sp_dai = _create_token(
        symbol='spDAI_partial',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=dai_addr,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    sp_debt = _create_token(
        symbol='variableDebtSparkDAI_partial',
        name='Spark Debt DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=dai_addr,
        flag=AssetFlag.ACCRUING_INTEREST_DEBT,
    )
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[sp_dai, sp_debt],
        )

    with database.conn.read_ctx() as cursor:
        saved_addr1, _ = database.get_tokens_for_address(
            cursor=cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            token_exceptions=set(),
        )
    assert saved_addr1 is not None
    expected_addr1_raw = [7 * 10**18 if t == sp_dai else 2 * 10**18 for t in saved_addr1]

    with (
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL)), (True, _encode_address(SPARK_ETH_POOL))],
                [
                    (True, _encode_tokens_balance(expected_addr1_raw)),
                    (False, b''),                  # first index reverted
                    (True, _encode_uint256(0)),    # second index returned 0 (invalid)
                ],
            ],
        ),
        patch('rotkehlchen.chain.evm.tokens.Inquirer.find_main_currency_prices', return_value={}),
    ):
        balances, _ = tokens.query_tokens_for_addresses([TEST_ADDR1])

    assert balances == {TEST_ADDR1: {sp_dai: FVal(7), sp_debt: FVal(2)}}
    observations = get_wallet_observations(database)
    assert observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier].observation_index is None
    debt_obs = observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_debt.identifier]
    assert debt_obs.observation_index is None


def test_query_tokens_balance_subcall_failure_raises_and_writes_nothing(tokens, database) -> None:
    """A failed tokensBalance sub-call inside multicall_2 must fail closed and write no observations."""  # noqa: E501
    sp_dai = _create_token(
        symbol='spDAI_failbal',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[sp_dai],
        )

    with (
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL))],
                [
                    (False, b''),
                    (True, _encode_uint256(RAY_SUPPLY)),
                ],
            ],
        ),
        pytest.raises(RemoteError),
    ):
        tokens.query_tokens_for_addresses([TEST_ADDR1])

    assert get_wallet_observations(database) == {}


def test_query_tokens_multi_chunk_isolates_index_per_address(tokens, database) -> None:
    """When two addresses hold the same accruing token in separate chunks (different blocks),
    each address keeps the index captured in its own chunk and POOL() is only queried once."""
    sp_dai = _create_token(
        symbol='spDAI_chunks',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    with database.user_write() as write_cursor:
        for addr in (TEST_ADDR1, TEST_ADDR2):
            database.save_tokens_for_address(
                write_cursor=write_cursor,
                address=addr,
                blockchain=SupportedBlockchain.ETHEREUM,
                tokens=[sp_dai],
            )

    with (
        # Chunk size 8 forces one (address, [sp_dai]) entry per chunk (7 + 1 = 8).
        patch.object(tokens, '_get_token_detection_chunk_size_call_order', return_value=(8, [])),
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL))],
                [(True, _encode_tokens_balance([4 * 10**18])), (True, _encode_uint256(RAY_SUPPLY))],  # noqa: E501
                [(True, _encode_tokens_balance([9 * 10**18])), (True, _encode_uint256(RAY_LIDO))],
            ],
        ) as mock_multicall_2,
        patch('rotkehlchen.chain.evm.tokens.Inquirer.find_main_currency_prices', return_value={}),
    ):
        tokens.query_tokens_for_addresses([TEST_ADDR1, TEST_ADDR2])

    assert mock_multicall_2.call_count == 3  # 1 metadata + 2 atomic chunk calls
    observations = get_wallet_observations(database)
    assert observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier].observation_index == RAY_SUPPLY  # noqa: E501
    assert observations[LOCATION_ETHEREUM, TEST_ADDR2, sp_dai.identifier].observation_index == RAY_LIDO  # noqa: E501


def test_query_tokens_splits_accruing_chunk_on_request_too_large(tokens, database) -> None:
    """RequestTooLargeError on an accruing multicall_2 splits into smaller atomic sub-chunks."""
    sp_dai = _create_token(
        symbol='spDAI_split',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    dai = A_DAI.resolve_to_evm_token()
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[dai, sp_dai],
        )

    with (
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL))],
                RequestTooLargeError('too large'),
                [(True, _encode_tokens_balance([11 * 10**18])), (True, _encode_uint256(RAY_SUPPLY))],  # noqa: E501
            ],
        ) as mock_multicall_2,
        patch.object(
            tokens.evm_inquirer,
            'multicall',
            return_value=[_encode_tokens_balance([6 * 10**18])],
        ) as mock_multicall,
        patch('rotkehlchen.chain.evm.tokens.Inquirer.find_main_currency_prices', return_value={}),
    ):
        balances, _ = tokens.query_tokens_for_addresses([TEST_ADDR1])

    # Split produces [dai] (standard multicall) + [sp_dai] (atomic multicall_2).
    assert mock_multicall.call_count == 1
    assert mock_multicall_2.call_count == 3  # 1 metadata + 1 failed full chunk + 1 split chunk
    assert balances == {TEST_ADDR1: {dai: FVal(6), sp_dai: FVal(11)}}
    observations = get_wallet_observations(database)
    assert observations[LOCATION_ETHEREUM, TEST_ADDR1, dai.identifier].observation_index is None
    assert observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier].observation_index == RAY_SUPPLY  # noqa: E501


def test_query_new_tokens_atomic_balance_and_index_capture(tokens, database) -> None:
    """_query_new_tokens reuses tokens_balance + reserveIndex multicall for newly detected
    non-zero accruing tokens and persists the refreshed same-block amount + observation_index."""
    dai = A_DAI.resolve_to_evm_token()
    sp_dai = _create_token(
        symbol='spDAI_detect',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=dai.evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    erc20_candidates = [
        EvmTokenDetectionData(dai.identifier, dai.evm_address, 18),
        EvmTokenDetectionData(sp_dai.identifier, sp_dai.evm_address, 18),
    ]

    with (
        patch.object(
            GlobalDBHandler,
            'get_token_detection_data',
            return_value=(erc20_candidates, []),
        ),
        patch.object(tokens, 'maybe_detect_proxies_tokens'),
        # BalanceScanner initially saw 10 sp_dai and 5 dai.
        patch.object(
            tokens,
            '_detect_tokens',
            return_value=(
                {TEST_ADDR1: [dai, sp_dai]},
                set(),
                {TEST_ADDR1: {dai: FVal(5), sp_dai: FVal(10)}},
            ),
        ),
        # 1st call: POOL() metadata; 2nd call: atomic tokens_balance (10.05 sp_dai) + RAY_SUPPLY.
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL))],
                [
                    (True, _encode_tokens_balance([1005 * 10**16])),
                    (True, _encode_uint256(RAY_SUPPLY)),
                ],
            ],
        ) as mock_multicall_2,
    ):
        tokens._query_new_tokens([TEST_ADDR1])

    assert mock_multicall_2.call_count == 2
    assert len(mock_multicall_2.call_args_list[1].kwargs['calls']) == 2  # 1 tokens_balance + 1 index  # noqa: E501
    observations = get_wallet_observations(database)
    obs_dai = observations[LOCATION_ETHEREUM, TEST_ADDR1, dai.identifier]
    obs_sp_dai = observations[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier]
    assert obs_dai.amount == FVal(5)
    assert obs_dai.observation_index is None
    assert obs_sp_dai.amount == FVal('10.05')
    assert obs_sp_dai.observation_index == RAY_SUPPLY
    assert obs_sp_dai.source == ObservationSource.TOKEN_DETECTION
    assert obs_sp_dai.observation_id == obs_dai.observation_id

    # Cache row also reflects the refreshed atomic balance.
    with database.conn.read_ctx() as cursor:
        cached_amount = cursor.execute(
            'SELECT amount FROM blockchain_balances_cache '
            'WHERE blockchain=? AND address=? AND asset=?',
            (SupportedBlockchain.ETHEREUM.serialize(), TEST_ADDR1, sp_dai.identifier),
        ).fetchone()[0]
    assert FVal(cached_amount) == FVal('10.05')


def test_query_new_tokens_non_accruing_makes_zero_extra_calls(tokens, database) -> None:
    """When token detection finds no accruing tokens, no follow-up multicall_2 is executed."""
    dai = A_DAI.resolve_to_evm_token()
    erc20_candidates = [EvmTokenDetectionData(dai.identifier, dai.evm_address, 18)]

    with (
        patch.object(
            GlobalDBHandler,
            'get_token_detection_data',
            return_value=(erc20_candidates, []),
        ),
        patch.object(tokens, 'maybe_detect_proxies_tokens'),
        patch.object(
            tokens,
            '_detect_tokens',
            return_value=({TEST_ADDR1: [dai]}, set(), {TEST_ADDR1: {dai: FVal(3)}}),
        ),
        patch.object(tokens.evm_inquirer, 'multicall_2') as mock_multicall_2,
    ):
        tokens._query_new_tokens([TEST_ADDR1])

    mock_multicall_2.assert_not_called()
    obs = get_wallet_observations(database)[LOCATION_ETHEREUM, TEST_ADDR1, dai.identifier]
    assert obs.amount == FVal(3)
    assert obs.observation_index is None


@pytest.mark.parametrize('metadata_fails', [True, False])
def test_query_new_tokens_followup_failure_degrades_gracefully(
        tokens,
        database,
        metadata_fails: bool,
) -> None:
    """If either metadata resolution or the follow-up atomic multicall raises RemoteError,
    detection still persists balances with observation_index=None and makes no fallback multicall."""  # noqa: E501
    sp_dai = _create_token(
        symbol='spDAI_detect_fail',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    erc20_candidates = [EvmTokenDetectionData(sp_dai.identifier, sp_dai.evm_address, 18)]
    multicall_2_side_effect = (
        [RemoteError('rpc unavailable', cause=FailureCause.NETWORK)]
        if metadata_fails
        else [
            [(True, _encode_address(SPARK_ETH_POOL))],
            RemoteError('rpc unavailable', cause=FailureCause.NETWORK),
            RemoteError('indexer unavailable', cause=FailureCause.NETWORK),
        ]
    )

    with (
        patch.object(
            GlobalDBHandler,
            'get_token_detection_data',
            return_value=(erc20_candidates, []),
        ),
        patch.object(tokens, 'maybe_detect_proxies_tokens'),
        patch.object(
            tokens,
            '_detect_tokens',
            return_value=({TEST_ADDR1: [sp_dai]}, set(), {TEST_ADDR1: {sp_dai: FVal(12)}}),
        ),
        patch.object(tokens.evm_inquirer, 'multicall') as mock_multicall,
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=multicall_2_side_effect,
        ),
    ):
        tokens._query_new_tokens([TEST_ADDR1])

    mock_multicall.assert_not_called()
    obs = get_wallet_observations(database)[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier]
    assert obs.amount == FVal(12)
    assert obs.observation_index is None
    assert obs.source == ObservationSource.TOKEN_DETECTION


def test_query_new_tokens_atomic_zero_balance_drops_stale_detection(tokens, database) -> None:
    """If an accruing token's balance drops to 0 before the atomic follow-up multicall,
    it is dropped from cached balances and saved detected tokens."""
    sp_dai = _create_token(
        symbol='spDAI_detect_zero',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    # Seed as previously held so record_token_detection_observations certifies its 0 balance.
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[sp_dai],
        )
    erc20_candidates = [EvmTokenDetectionData(sp_dai.identifier, sp_dai.evm_address, 18)]

    with (
        patch.object(
            GlobalDBHandler,
            'get_token_detection_data',
            return_value=(erc20_candidates, []),
        ),
        patch.object(tokens, 'maybe_detect_proxies_tokens'),
        patch.object(
            tokens,
            '_detect_tokens',
            return_value=({TEST_ADDR1: [sp_dai]}, set(), {TEST_ADDR1: {sp_dai: FVal(1)}}),
        ),
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL))],
                [
                    (True, _encode_tokens_balance([0])),
                    (True, _encode_uint256(RAY_SUPPLY)),
                ],
            ],
        ),
    ):
        tokens._query_new_tokens([TEST_ADDR1])

    obs = get_wallet_observations(database)[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier]
    assert obs.amount == ZERO
    assert obs.observation_index == RAY_SUPPLY
    with database.conn.read_ctx() as cursor:
        saved_tokens, _ = database.get_tokens_for_address(
            cursor=cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            token_exceptions=set(),
        )
    assert saved_tokens == []


def test_query_tokens_accruing_chunk_falls_back_to_indexer_on_remote_error(
        tokens,
        database,
) -> None:
    """When RPC-only call_order fails with RemoteError on an accruing multicall_2, it falls back
    to indexers_node (matching EvmNodeInquirer.multicall) and records both balance and index."""
    sp_dai = _create_token(
        symbol='spDAI_fallback',
        name='Spark DAI',
        decimals=18,
        protocol=CPT_SPARK,
        underlying=A_DAI.resolve_to_evm_token().evm_address,
        flag=AssetFlag.ACCRUING_INTEREST_SUPPLY,
    )
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=TEST_ADDR1,
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[sp_dai],
        )

    rpc_only_order = [MagicMock(node_info=MagicMock(name='rpc_node'))]
    rpc_only_order[0].node_info.name = 'rpc_node'

    with (
        patch.object(
            tokens,
            '_get_token_detection_chunk_size_call_order',
            return_value=(100, rpc_only_order),
        ),
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=[
                [(True, _encode_address(SPARK_ETH_POOL))],
                RemoteError('rpc timeout', cause=FailureCause.NETWORK),
                [
                    (True, _encode_tokens_balance([8 * 10**18])),
                    (True, _encode_uint256(RAY_SUPPLY)),
                ],
            ],
        ) as mock_multicall_2,
        patch('rotkehlchen.chain.evm.tokens.Inquirer.find_main_currency_prices', return_value={}),
    ):
        balances, _ = tokens.query_tokens_for_addresses([TEST_ADDR1])

    assert mock_multicall_2.call_count == 3
    assert mock_multicall_2.call_args_list[1].kwargs['call_order'] == rpc_only_order
    assert mock_multicall_2.call_args_list[2].kwargs['call_order'] == [
        tokens.evm_inquirer.indexers_node,
    ]
    assert balances == {TEST_ADDR1: {sp_dai: FVal(8)}}
    obs = get_wallet_observations(database)[LOCATION_ETHEREUM, TEST_ADDR1, sp_dai.identifier]
    assert obs.amount == FVal(8)
    assert obs.observation_index == RAY_SUPPLY

    # When indexers_node is already in call_order, RemoteError propagates without duplicate retry.
    indexer_order = [tokens.evm_inquirer.indexers_node]
    with (
        patch.object(
            tokens,
            '_get_token_detection_chunk_size_call_order',
            return_value=(100, indexer_order),
        ),
        patch.object(
            tokens.evm_inquirer,
            'multicall_2',
            side_effect=RemoteError('indexer down', cause=FailureCause.NETWORK),
        ) as mock_multicall_2_fail,
        pytest.raises(RemoteError),
    ):
        tokens.query_tokens_for_addresses([TEST_ADDR1])

    assert mock_multicall_2_fail.call_count == 1
