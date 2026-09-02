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

  /**
   * Follows the wallet onto a chain rotki supports.
   *
   * @remarks
   * A chain rotki does not support leaves the selection alone, so that {@link wrongNetwork} reports
   * the mismatch; adopting a fallback would hide it. No `curr === prev` guard is needed, since
   * `connectedChainId` is a plain ref and Vue does not fire on a write of the value it already holds.
   *
   * @param curr - the chain id the wallet now reports, if it reports one
   */
  function followWalletChain(curr: number | undefined): void {
    if (!isDefined(curr))
      return;

    const chain = getChainFromChainId(curr);
    if (chain)
      set(selectedChain, chain);
  }

  watchImmediate(connectedChainId, followWalletChain);

  return {
    switchToSelectedChain,
    wrongNetwork,
  };
}
