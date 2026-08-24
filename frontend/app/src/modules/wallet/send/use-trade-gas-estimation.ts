import type { ComputedRef, Ref } from 'vue';
import type { GasFeeEstimation } from '@/modules/wallet/types';
import { logger } from '@/modules/core/common/logging/logging';
import { getWalletErrorMessage } from '@/modules/wallet/constants';
import { useWalletHelper } from '@/modules/wallet/use-wallet-helper';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

/** Rejection used to unwind an estimation the user has already moved past. */
const CANCELLED = 'Gas estimation cancelled';

interface UseTradeGasEstimationOptions {
  /** The asset the estimate is about; a change while one is pending invalidates it. */
  readonly asset: Ref<string>;
  /** The chain the estimate is for; gas is only estimated on the connected chain. */
  readonly chain: Ref<string>;
  /** Whether the selected asset is the chain's native token; only then does gas apply. */
  readonly isNativeAsset: Ref<boolean>;
  /** Whether the selected asset resolved to a known one. Estimating before it does is pointless. */
  readonly isAssetResolved: Ref<boolean>;
}

interface UseTradeGasEstimationReturn {
  readonly estimatedGasFee: Readonly<Ref<string>>;
  readonly estimatingGas: Readonly<Ref<boolean>>;
  /** Whether a gas estimate can be produced at all for the current selection. */
  readonly gasEstimable: ComputedRef<boolean>;
}

/**
 * Keeps a gas estimate for the selected asset and chain.
 *
 * Estimation is inherently racy: the user can switch asset or chain while a request is in flight.
 * Two guards keep a late answer from overwriting a newer selection - the previous request is
 * aborted when a new one starts, and the resolved estimate is dropped if the asset changed while
 * it was pending.
 */
export function useTradeGasEstimation(options: UseTradeGasEstimationOptions): UseTradeGasEstimationReturn {
  const { asset, chain, isAssetResolved, isNativeAsset } = options;

  const estimatedGasFee = shallowRef<string>('0');
  const estimatingGas = shallowRef<boolean>(false);
  const controller = shallowRef<AbortController>();

  const { getChainIdFromChain } = useWalletHelper();
  const { connected, connectedChainId } = storeToRefs(useWalletStore());
  const { getGasFeeForChain } = useWalletStore();

  function resetFee(): void {
    set(estimatedGasFee, '0');
  }

  // Nothing should stay in flight once the card is gone.
  onScopeDispose(() => {
    get(controller)?.abort();
  });

  /** Gas can only be estimated once a wallet is connected and a resolvable asset is selected. */
  const gasEstimable = computed<boolean>(() =>
    get(connected) && !!get(chain) && !!get(asset) && get(isAssetResolved),
  );

  async function estimate(currentAsset: string): Promise<GasFeeEstimation | undefined> {
    const abortController = new AbortController();
    set(controller, abortController);
    set(estimatingGas, true);

    const aborted = new Promise<GasFeeEstimation>((_, reject) => {
      abortController.signal.addEventListener('abort', () => {
        reject(new Error(CANCELLED));
      });
    });

    const estimation = await Promise.race([getGasFeeForChain(), aborted]);

    // The selection moved on while this was in flight, so the answer is no longer about it.
    if (currentAsset !== get(asset))
      return undefined;

    return estimation;
  }

  watchImmediate([asset, chain, connectedChainId], async ([currentAsset, currentChain, currentChainId]) => {
    if (!get(gasEstimable))
      return;

    get(controller)?.abort();

    if (!get(isNativeAsset)) {
      resetFee();
      return;
    }

    try {
      // Both sides can be undefined (an unresolvable chain, a wallet that has not
      // reported its chain yet). That is not a match: estimating then would price
      // the transaction on a chain nothing has confirmed.
      const selectedChainId = getChainIdFromChain(currentChain);
      if (selectedChainId !== undefined && selectedChainId === currentChainId) {
        const estimation = await estimate(currentAsset);
        if (estimation) {
          set(estimatedGasFee, estimation.gasFee);
          return;
        }
      }

      resetFee();
    }
    catch (error: unknown) {
      if (getWalletErrorMessage(error) !== CANCELLED) {
        resetFee();
        logger.error(error);
      }
    }
    finally {
      set(controller, undefined);
      set(estimatingGas, false);
    }
  });

  return {
    estimatedGasFee: readonly(estimatedGasFee),
    estimatingGas: readonly(estimatingGas),
    gasEstimable,
  };
}
