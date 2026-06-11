"""The whale profile: a long-time power user. Scaling-behavior gate.

~400k history events over ~6 years, 20 EVM accounts active on 4 chains plus
5 BTC accounts, 3 exchanges. All distribution constants live here on purpose
(design §3.2): they are the reviewable model of what a heavy real account
looks like — adjust them when a real-world bug reveals a shape gap.
"""
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, SupportedBlockchain
from tools.scenarios.deterministic import DeterministicFactory, monthly_ramp_weights
from tools.scenarios.profiles.common import (
    MODULE_TOKEN_PRICES,
    USD_PRICES,
    EvmPools,
    erc20,
    make_asset_movement,
    make_evm_tx_group,
    make_exchange_swap,
    make_snapshots,
    make_staking_reward,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from tools.scenarios.base import ProfileBuilder

SEED: Final = 2001
ACTIVE_MONTHS: Final = 72  # six years of history

N_EVM_ACCOUNTS: Final = 20
N_BTC_ACCOUNTS: Final = 5

# Row-count targets per category (~400k total)
EVM_ROWS_TARGET: Final = 300_000
SWAP_ROWS_TARGET: Final = 52_000
MOVEMENT_ROWS_TARGET: Final = 24_000
REWARD_ROWS_TARGET: Final = 24_000

# Events per EVM transaction (incl. the gas event); long tail of busy txs
TX_GROUP_SIZES: Final = (1, 2, 3, 4, 5, 6, 8, 12)
TX_GROUP_SIZE_WEIGHTS: Final = (0.30, 0.27, 0.17, 0.10, 0.07, 0.05, 0.03, 0.01)

# Chain activity split (multichain user, mainnet-heavy)
CHAINS: Final = (
    Location.ETHEREUM,
    Location.ARBITRUM_ONE,
    Location.OPTIMISM,
    Location.BASE,
)
CHAIN_WEIGHTS: Final = (0.55, 0.18, 0.14, 0.13)
CHAIN_IDS: Final = {Location.ETHEREUM: 1, Location.ARBITRUM_ONE: 42161, Location.OPTIMISM: 10, Location.BASE: 8453}  # noqa: E501

# A few accounts do most of the activity (zipf-ish), like real wallets
ACCOUNT_WEIGHTS: Final = tuple(1.0 / rank for rank in range(1, N_EVM_ACCOUNTS + 1))

SWAP_FEE_SHARE: Final = 0.3
MOVEMENT_FEE_SHARE: Final = 0.5

EXCHANGES: Final = (Location.KRAKEN, Location.BINANCE, Location.COINBASE)
EXCHANGE_WEIGHTS: Final = (0.5, 0.35, 0.15)

# Counterparty pools with zipf-ish skew: a handful of protocols dominate
DEX_COUNTERPARTIES: Final = (
    'uniswap-v3', 'uniswap-v2', '1inch-v5', 'cowswap', 'paraswap', 'kyber',
    '0x', 'sushiswap', 'balancer-v2', 'odos',
)
DEFI_COUNTERPARTIES: Final = (
    'aave-v3', 'lido', 'curve', 'compound-v3', 'makerdao', 'convex',
    'yearn-v2', 'rocketpool', 'eigenlayer', 'morpho', 'spark', 'pendle',
)

# (identifier, symbol) pools per chain; checked against the global DB at build
MAINNET_ERC20_POOL: Final = (
    (erc20(1, '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'), 'USDC'),
    (erc20(1, '0xdAC17F958D2ee523a2206206994597C13D831ec7'), 'USDT'),
    (erc20(1, '0x6B175474E89094C44Da98b954EedeAC495271d0F'), 'DAI'),
    (erc20(1, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'), 'WETH'),
    (erc20(1, '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'), 'WBTC'),
    (erc20(1, '0x514910771AF9Ca656af840dff83E8264EcF986CA'), 'LINK'),
    (erc20(1, '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'), 'UNI'),
    (erc20(1, '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'), 'AAVE'),
    (erc20(1, '0xD533a949740bb3306d119CC777fa900bA034cd52'), 'CRV'),
    (erc20(1, '0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32'), 'LDO'),
    (erc20(1, '0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'), 'MKR'),
    (erc20(1, '0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'), 'SNX'),
    (erc20(1, '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'), 'stETH'),
    (erc20(1, '0xae78736Cd615f374D3085123A210448E74Fc6393'), 'rETH'),
    (erc20(1, '0x6982508145454Ce325dDbE47a25d4ec3d2311933'), 'PEPE'),
)
L2_ERC20_POOLS: Final = {
    Location.ARBITRUM_ONE: (
        (erc20(42161, '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'), 'USDC'),
        (erc20(42161, '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'), 'WETH'),
        (erc20(42161, '0x912CE59144191C1204E64559FE8253a0e49E6548'), 'ARB'),
    ),
    Location.OPTIMISM: (
        (erc20(10, '0x7F5c764cBc14f9669B88837ca1490cCa17c31607'), 'USDC.e'),
        (erc20(10, '0x4200000000000000000000000000000000000006'), 'WETH'),
        (erc20(10, '0x4200000000000000000000000000000000000042'), 'OP'),
    ),
    Location.BASE: (
        (erc20(8453, '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'), 'USDC'),
        (erc20(8453, '0x4200000000000000000000000000000000000006'), 'WETH'),
    ),
}


def _zipf(count: int) -> tuple[float, ...]:
    return tuple(1.0 / rank for rank in range(1, count + 1))


def build(builder: 'ProfileBuilder') -> dict[str, Any] | None:
    factory = DeterministicFactory(SEED)
    evm_accounts = [factory.evm_address() for _ in range(N_EVM_ACCOUNTS)]
    builder.add_accounts(
        [
            BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=account,
                label=f'Wallet {idx + 1}',
            )
            for idx, account in enumerate(evm_accounts)
        ] + [
            BlockchainAccountData(
                chain=SupportedBlockchain.BITCOIN,
                address=factory.btc_address(),
                label=f'BTC {idx + 1}',
            )
            for idx in range(N_BTC_ACCOUNTS)
        ],
    )

    def chain_pools(location: Location) -> EvmPools:
        candidates = MAINNET_ERC20_POOL if location == Location.ETHEREUM else L2_ERC20_POOLS[location]  # noqa: E501
        existing = set(builder.filter_existing_assets([x[0] for x in candidates]))
        assets = [(Asset(identifier), symbol) for identifier, symbol in candidates if identifier in existing]  # noqa: E501
        return EvmPools(
            dex_counterparties=DEX_COUNTERPARTIES,
            dex_weights=_zipf(len(DEX_COUNTERPARTIES)),
            defi_counterparties=DEFI_COUNTERPARTIES,
            defi_weights=_zipf(len(DEFI_COUNTERPARTIES)),
            assets=[(A_ETH, 'ETH'), *assets],
            asset_weights=[3.0, *_zipf(len(assets))],
            gas_asset=A_ETH,
        )

    pools_per_chain = {location: chain_pools(location) for location in CHAINS}

    builder.add_manual_balances([
        ManuallyTrackedBalance(
            identifier=-1,
            asset=Asset('EUR'),
            label='Bank account',
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
            amount=FVal('100000'),
        ),
        ManuallyTrackedBalance(
            identifier=-1,
            asset=A_BTC,
            label='Hardware wallet',
            location=Location.BLOCKCHAIN,
            tags=None,
            balance_type=BalanceType.ASSET,
            amount=FVal('4.2'),
        ),
    ])
    price_assets = {
        symbol: asset
        for pools in pools_per_chain.values()
        for asset, symbol in pools.assets
    }
    builder.add_manual_latest_prices(
        [(asset, USD_PRICES[symbol]) for symbol, asset in price_assets.items()]
        + [(Asset('EUR'), USD_PRICES['EUR']), (A_BTC, USD_PRICES['BTC'])]
        + [
            (Asset(identifier), USD_PRICES[symbol])
            for identifier, symbol in MODULE_TOKEN_PRICES
            if identifier in set(builder.filter_existing_assets(
                [x[0] for x in MODULE_TOKEN_PRICES]))
        ],
    )
    balance_rows, location_rows, snapshot_count = make_snapshots(
        factory=factory,
        assets=pools_per_chain[Location.ETHEREUM].assets,
        weeks=ACTIVE_MONTHS * 52 // 12,
        location_weights=(
            (Location.BLOCKCHAIN, 0.55),
            (Location.KRAKEN, 0.2),
            (Location.BINANCE, 0.15),
            (Location.COINBASE, 0.1),
        ),
    )
    builder.add_balance_snapshots(balance_rows, location_rows, snapshot_count)

    month_indices = range(ACTIVE_MONTHS)
    month_weights = monthly_ramp_weights(ACTIVE_MONTHS)

    def random_timestamp() -> 'Any':
        return factory.timestamp_ms_in_month(
            factory.weighted_choice(month_indices, month_weights),
        )

    def generate() -> 'Iterator[HistoryBaseEntry]':
        rows = 0
        while rows < EVM_ROWS_TARGET:
            location = factory.weighted_choice(CHAINS, CHAIN_WEIGHTS)
            group = make_evm_tx_group(
                factory=factory,
                pools=pools_per_chain[location],
                location=location,
                account=factory.weighted_choice(evm_accounts, ACCOUNT_WEIGHTS),
                timestamp=random_timestamp(),
                size=factory.weighted_choice(TX_GROUP_SIZES, TX_GROUP_SIZE_WEIGHTS),
            )
            rows += len(group)
            yield from group

        rows, idx = 0, 0
        mainnet_pools = pools_per_chain[Location.ETHEREUM]
        while rows < SWAP_ROWS_TARGET:
            group = make_exchange_swap(
                factory=factory,
                location=factory.weighted_choice(EXCHANGES, EXCHANGE_WEIGHTS),
                timestamp=random_timestamp(),
                spend=factory.weighted_choice(mainnet_pools.assets, mainnet_pools.asset_weights),
                receive=factory.weighted_choice(mainnet_pools.assets, mainnet_pools.asset_weights),
                unique_suffix=str(idx),
                fee_asset=A_ETH if factory.rng.random() < SWAP_FEE_SHARE else None,
            )
            rows += len(group)
            idx += 1
            yield from group

        rows, idx = 0, 0
        while rows < MOVEMENT_ROWS_TARGET:
            group = make_asset_movement(
                factory=factory,
                location=factory.weighted_choice(EXCHANGES, EXCHANGE_WEIGHTS),
                timestamp=random_timestamp(),
                asset=factory.weighted_choice(mainnet_pools.assets, mainnet_pools.asset_weights),
                is_deposit=factory.rng.random() < 0.5,
                unique_suffix=str(idx),
                with_fee=factory.rng.random() < MOVEMENT_FEE_SHARE,
            )
            rows += len(group)
            idx += 1
            yield from group

        for idx in range(REWARD_ROWS_TARGET):
            yield make_staking_reward(
                factory=factory,
                location=factory.weighted_choice(EXCHANGES, EXCHANGE_WEIGHTS),
                timestamp=random_timestamp(),
                asset=(A_ETH, 'ETH'),
                unique_suffix=str(idx),
            )

    builder.add_history_events(generate())
    return {'evm_accounts': evm_accounts}
