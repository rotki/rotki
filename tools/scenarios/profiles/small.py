"""The small profile: the default-config common user. Primary perf gate.

4 ETH + 1 BTC accounts, a few manual balances, exchange trades on two
exchanges, ~500 history events total, a couple of ignored assets.
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
    EvmPools,
    erc20,
    make_asset_movement,
    make_evm_tx_group,
    make_exchange_swap,
    make_staking_reward,
)

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from tools.scenarios.base import ProfileBuilder

SEED: Final = 1001
ACTIVE_MONTHS: Final = 24  # two years of history

N_ETH_ACCOUNTS: Final = 4
N_EVM_TX_GROUPS: Final = 80
TX_GROUP_SIZES: Final = (1, 2, 3, 4)
TX_GROUP_SIZE_WEIGHTS: Final = (0.45, 0.30, 0.15, 0.10)
N_EXCHANGE_SWAPS: Final = 90
SWAP_FEE_SHARE: Final = 0.3
N_ASSET_MOVEMENTS: Final = 20
MOVEMENT_FEE_SHARE: Final = 0.5
N_STAKING_REWARDS: Final = 80

EXCHANGES: Final = (Location.KRAKEN, Location.BINANCE)
EXCHANGE_WEIGHTS: Final = (0.6, 0.4)

# (identifier, symbol) — mainnet majors only; checked against the global DB at build
ERC20_POOL: Final = (
    (erc20(1, '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'), 'USDC'),
    (erc20(1, '0xdAC17F958D2ee523a2206206994597C13D831ec7'), 'USDT'),
    (erc20(1, '0x6B175474E89094C44Da98b954EedeAC495271d0F'), 'DAI'),
    (erc20(1, '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'), 'WETH'),
    (erc20(1, '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'), 'WBTC'),
    (erc20(1, '0x514910771AF9Ca656af840dff83E8264EcF986CA'), 'LINK'),
    (erc20(1, '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'), 'UNI'),
)
IGNORED_ASSET_CANDIDATES: Final = (
    erc20(1, '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'),  # SHIB
    erc20(1, '0x4Fabb145d64652a948d72533023f6E7A623C7C53'),  # BUSD
)

DEX_COUNTERPARTIES: Final = ('uniswap-v3', 'uniswap-v2', 'cowswap')
DEX_WEIGHTS: Final = (0.5, 0.3, 0.2)
DEFI_COUNTERPARTIES: Final = ('aave-v3', 'lido', 'curve')
DEFI_WEIGHTS: Final = (0.5, 0.3, 0.2)


def build(builder: 'ProfileBuilder') -> dict[str, Any] | None:
    factory = DeterministicFactory(SEED)
    eth_accounts = [factory.evm_address() for _ in range(N_ETH_ACCOUNTS)]
    builder.add_accounts(
        [
            BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=account,
                label=f'Hot wallet {idx + 1}',
            )
            for idx, account in enumerate(eth_accounts)
        ] + [BlockchainAccountData(
            chain=SupportedBlockchain.BITCOIN,
            address=factory.btc_address(),
            label='Cold storage',
        )],
    )
    builder.add_manual_balances([
        ManuallyTrackedBalance(
            identifier=-1,
            asset=Asset('EUR'),
            label='Bank savings',
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
            amount=FVal('12500'),
        ),
        ManuallyTrackedBalance(
            identifier=-1,
            asset=A_BTC,
            label='Paper wallet',
            location=Location.BLOCKCHAIN,
            tags=None,
            balance_type=BalanceType.ASSET,
            amount=FVal('0.35'),
        ),
    ])
    builder.ignore_assets(builder.filter_existing_assets(IGNORED_ASSET_CANDIDATES))

    asset_pool = [
        (Asset(identifier), symbol)
        for identifier, symbol in ERC20_POOL
        if identifier in set(builder.filter_existing_assets([x[0] for x in ERC20_POOL]))
    ]
    pools = EvmPools(
        dex_counterparties=DEX_COUNTERPARTIES,
        dex_weights=DEX_WEIGHTS,
        defi_counterparties=DEFI_COUNTERPARTIES,
        defi_weights=DEFI_WEIGHTS,
        assets=[(A_ETH, 'ETH'), *asset_pool],
        asset_weights=[2.0] + [1.0] * len(asset_pool),
        gas_asset=A_ETH,
    )
    month_indices = range(ACTIVE_MONTHS)
    month_weights = monthly_ramp_weights(ACTIVE_MONTHS)

    def generate() -> 'list[HistoryBaseEntry]':
        events: list[HistoryBaseEntry] = []
        for _ in range(N_EVM_TX_GROUPS):
            events.extend(make_evm_tx_group(
                factory=factory,
                pools=pools,
                location=Location.ETHEREUM,
                account=factory.weighted_choice(eth_accounts, [1.0] * len(eth_accounts)),
                timestamp=factory.timestamp_ms_in_month(
                    factory.weighted_choice(month_indices, month_weights),
                ),
                size=factory.weighted_choice(TX_GROUP_SIZES, TX_GROUP_SIZE_WEIGHTS),
            ))
        for idx in range(N_EXCHANGE_SWAPS):
            events.extend(make_exchange_swap(
                factory=factory,
                location=factory.weighted_choice(EXCHANGES, EXCHANGE_WEIGHTS),
                timestamp=factory.timestamp_ms_in_month(
                    factory.weighted_choice(month_indices, month_weights),
                ),
                spend=factory.weighted_choice(pools.assets, pools.asset_weights),
                receive=factory.weighted_choice(pools.assets, pools.asset_weights),
                unique_suffix=str(idx),
                fee_asset=A_ETH if factory.rng.random() < SWAP_FEE_SHARE else None,
            ))
        for idx in range(N_ASSET_MOVEMENTS):
            events.extend(make_asset_movement(
                factory=factory,
                location=factory.weighted_choice(EXCHANGES, EXCHANGE_WEIGHTS),
                timestamp=factory.timestamp_ms_in_month(
                    factory.weighted_choice(month_indices, month_weights),
                ),
                asset=factory.weighted_choice(pools.assets, pools.asset_weights),
                is_deposit=factory.rng.random() < 0.5,
                unique_suffix=str(idx),
                with_fee=factory.rng.random() < MOVEMENT_FEE_SHARE,
            ))
        events.extend(
            make_staking_reward(
                factory=factory,
                location=factory.weighted_choice(EXCHANGES, EXCHANGE_WEIGHTS),
                timestamp=factory.timestamp_ms_in_month(
                    factory.weighted_choice(month_indices, month_weights),
                ),
                asset=(A_ETH, 'ETH'),
                unique_suffix=str(idx),
            )
            for idx in range(N_STAKING_REWARDS)
        )
        return events

    builder.add_history_events(generate())
    return {'eth_accounts': eth_accounts}
