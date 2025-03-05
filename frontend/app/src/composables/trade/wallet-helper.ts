import type { Blockchain } from '@rotki/common';
import { useSupportedChains } from '@/composables/info/chains';

interface UseWalletHelperReturn {
  getChainFromChainId: (chainId: number) => Blockchain;
  getChainIdFromChain: (chain: Blockchain) => bigint;
}

export function useWalletHelper(): UseWalletHelperReturn {
  const { allEvmChains, getChain } = useSupportedChains();

  function getChainFromChainId(chainId: number): Blockchain {
    const name = get(allEvmChains).find(item => item.id === chainId)?.name || 'ethereum';
    return getChain(name);
  }

  const getChainIdFromChain = (chain: Blockchain): bigint => {
    const chainId = get(allEvmChains).find(item => item.name === chain)?.id || 1;
    return BigInt(chainId);
  };

  return {
    getChainFromChainId,
    getChainIdFromChain,
  };
}
