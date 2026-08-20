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
 * The wallet reports whatever chain it happens to sit on, which is not limited
 * to the chains rotki supports, so every path here has to cope with a chain id
 * that resolves to nothing. Resolving it to ethereum instead, as this used to,
 * made an unsupported chain look like mainnet: no warning appeared and the
 * selection silently followed the wallet onto the wrong chain.
 *
 * @param selectedChain the chain the send form is targeting, updated in place
 * when the wallet moves to a chain rotki does support.
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
    // Unreachable by construction: the selection only ever holds a chain from
    // `supportedChainsForConnectedAccount`, and every entry there was built by
    // pairing a chain *with* its numeric id. Log rather than return quietly, so
    // a broken invariant surfaces instead of becoming a button that does nothing.
    if (chainId === undefined) {
      logger.error(`no chain id for ${get(selectedChain)}, cannot switch network`);
      return;
    }

    startPromise(switchNetwork(BigInt(chainId)));
  }

  watchImmediate(connectedChainId, (curr, prev) => {
    if (!isDefined(curr) || curr === prev)
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
