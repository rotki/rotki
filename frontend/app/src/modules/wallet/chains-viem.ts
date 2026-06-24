import type { Chain } from '@/modules/wallet/viem-client';
import { arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from 'viem/chains';

/**
 * The viem {@link Chain} objects for the chains rotki's wallet stack supports.
 *
 * These are *static named* imports so Rollup tree-shakes `viem/chains` down to
 * just these definitions instead of bundling all ~700 chains viem ships (viem
 * is `sideEffects: false`; it exposes no per-chain subpath, and a dynamic keyed
 * access like `Reflect.get(import('viem/chains'), key)` would retain the whole
 * barrel). This module is only ever reached through a dynamic
 * `import('./chains-viem')`, so viem's chain data stays out of the initial
 * bundle and loads only when a wallet connection actually needs it.
 *
 * Keep the ids in sync with `SUPPORTED_WALLET_CHAIN_IDS` in `constants.ts`.
 */
export const SUPPORTED_WALLET_NETWORKS: readonly Chain[] = [
  mainnet,
  base,
  arbitrum,
  optimism,
  bsc,
  gnosis,
  polygon,
  scroll,
] as const;

export function getWalletNetwork(chainId: bigint): Chain | undefined {
  return SUPPORTED_WALLET_NETWORKS.find(network => BigInt(network.id) === chainId);
}
