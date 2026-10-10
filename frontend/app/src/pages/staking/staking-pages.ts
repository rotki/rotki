import type { Component } from 'vue';

export type StakingLocation = 'eth2' | 'liquity' | 'kraken' | 'lido-csm' | 'solana' | 'hyperliquid';

/**
 * The staking page each location resolves to, loaded on demand. Kept apart from the composable so
 * a spec can replace the whole map without pulling every page component into the module graph.
 */
export const stakingPages: Record<StakingLocation, Component> = {
  'eth2': defineAsyncComponent(async () => import('@/modules/staking/eth/EthStakingPage.vue')),
  'hyperliquid': defineAsyncComponent(async () => import('@/modules/staking/hyperliquid/HyperliquidPage.vue')),
  'kraken': defineAsyncComponent(async () => import('@/modules/staking/kraken/KrakenPage.vue')),
  'lido-csm': defineAsyncComponent(async () => import('@/modules/staking/lido-csm/LidoCsmPage.vue')),
  'liquity': defineAsyncComponent(async () => import('@/modules/staking/liquity/LiquityPage.vue')),
  'solana': defineAsyncComponent(async () => import('@/modules/staking/solana/SolanaPage.vue')),
};
