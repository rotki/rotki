import type { ComputedRef, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';
import { useWalletHelper } from '@/modules/wallet/use-wallet-helper';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

interface UseTradeNetworkMatchReturn {
  wrongNetwork: ComputedRef<boolean>;
  switchToSelectedChain: () => void;
}

/**
 * Keeps the selected chain and the chain the wallet is on in agreement.
 *
 * @remarks
 * The wallet reports whatever chain it sits on, which is not limited to the chains rotki supports,
 * so every path here has to cope with a chain id that resolves to nothing. Do not fall back to
 * ethereum: that makes an unsupported chain look like mainnet, so no warning appears and the
 * selection follows the wallet onto the wrong chain.
 *
 * @param selectedChain - the chain the send form is targeting, updated in place when the wallet
 * moves to a chain rotki does support.
 */
export function useTradeNetworkMatch(selectedChain: Ref<string>): UseTradeNetworkMatchReturn {
  const { getChainFromChainId, getChainIdFromChain } = useWalletHelper();

  const walletStore = useWalletStore();
  const { connected, connectedChainId } = storeToRefs(walletStore);
  const { switchNetwork } = walletStore;

  const wrongNetwork = computed<boolean>(() => {
    const chainId = get(connectedChainId);
    if (!get(connected) || !chainId)
      return false;

    // An unresolvable chain compares unequal, which is the answer we want: the
    // wallet is on something the form cannot send from.
    return get(selectedChain) !== getChainFromChainId(chainId);
  });

  function switchToSelectedChain(): void {
    const chainId = getChainIdFromChain(get(selectedChain));
    if (chainId === undefined) {
      logger.error(`no chain id for ${get(selectedChain)}, cannot switch network`);
      return;
    }

    startPromise(switchNetwork(BigInt(chainId)));
  }

  // No `curr === prev` guard: `connectedChainId` is a plain ref, so Vue does not
  // fire this when it is written with the value it already holds.
  watchImmediate(connectedChainId, (curr) => {
    if (!isDefined(curr))
      return;

    // Keep the selection where it is when the wallet moves somewhere rotki does
    // not support: `wrongNetwork` then reports the mismatch, where adopting a
    // fallback chain would have hidden it.
    const chain = getChainFromChainId(curr);
    if (chain)
      set(selectedChain, chain);
  });

  return {
    switchToSelectedChain,
    wrongNetwork,
  };
}
