import type { ComputedRef } from 'vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

/**
 * An EVM chain the wallet stack can operate on, paired with its EIP-155 id.
 */
interface WalletChain {
  /** the rotki blockchain id, e.g. `eth`, `monad` */
  chain: string;
  /** the numeric EIP-155 chain id, e.g. `1`, `143` */
  chainId: number;
}

interface UseWalletChainsReturn {
  walletChains: ComputedRef<WalletChain[]>;
  walletChainIds: ComputedRef<number[]>;
  getSessionChains: (chainIds?: number[]) => string[];
}

/**
 * The chains the wallet can send on, derived from what the backend reports
 * rather than from a hardcoded list, so a chain the backend gains needs no
 * frontend release.
 *
 * Two endpoints are joined because neither carries both halves:
 * `/blockchains/supported` names the chains but serializes no numeric id, and
 * `/blockchains/evm/all` carries the numeric id but iterates the whole `ChainID`
 * enum, which is far broader than the chains rotki actually supports. The join
 * key is `evmChainName`.
 *
 * The source is `txEvmChains`, not `evmChainsData`: that drops AVAX, which has
 * no transaction support, and a send finishes by recording the hash through
 * `addTransactionHash`.
 *
 * A chain with no matching numeric id is dropped. It must not fall back to
 * ethereum — that would label another chain's balance as an ethereum one.
 */
export function useWalletChains(): UseWalletChainsReturn {
  const { getEvmChainId, txEvmChains } = useSupportedChains();

  const walletChains = computed<WalletChain[]>(() => {
    const chains: WalletChain[] = [];
    for (const info of get(txEvmChains)) {
      const chainId = getEvmChainId(info.evmChainName);
      if (chainId !== undefined)
        chains.push({ chain: info.id, chainId });
    }
    return chains;
  });

  const walletChainIds = computed<number[]>(() => get(walletChains).map(item => item.chainId));

  /**
   * The chains usable by a connection that reports `chainIds`, or every chain
   * when it reports none (an injected wallet, or a session with no namespaces).
   *
   * This is an intersection rather than a mapping, so a chain the wallet offers
   * but rotki does not support is dropped instead of resolving to a wrong chain,
   * and the order stays rotki's (ethereum first).
   */
  const getSessionChains = (chainIds?: number[]): string[] => {
    const chains = get(walletChains);
    if (!chainIds?.length)
      return chains.map(item => item.chain);

    const sessionChainIds = new Set(chainIds);
    return chains.filter(item => sessionChainIds.has(item.chainId)).map(item => item.chain);
  };

  return {
    getSessionChains,
    walletChainIds,
    walletChains,
  };
}
