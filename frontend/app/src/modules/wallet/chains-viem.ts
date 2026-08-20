import type { Chain } from '@/modules/wallet/viem-client';
import { arbitrum, base, bsc, gnosis, hyperEvm, mainnet, monad, optimism, polygon, scroll } from 'viem/chains';

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
 * This is an *enrichment* table, not the list of chains the wallet offers: that
 * comes from the backend through `useWalletChains`. Only the RPC url and the
 * `wallet_addEthereumChain` payload need a definition from here, and both call
 * sites already handle a chain that has none. A chain the backend gains still
 * works without an entry; adding one only buys the "add this network to your
 * wallet" fallback.
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
  monad,
  hyperEvm,
] as const;

export function getWalletNetwork(chainId: bigint): Chain | undefined {
  return SUPPORTED_WALLET_NETWORKS.find(network => BigInt(network.id) === chainId);
}
