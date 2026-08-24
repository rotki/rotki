import type { BigNumber } from '@rotki/common';
import type { Ref } from 'vue';
import type { GetAssetBalancePayload } from '@/modules/wallet/types';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { maxSendableAmount } from '@/modules/wallet/send/trade-send-utils';
import { useTradeApi } from '@/modules/wallet/send/use-trade-api';

interface UseTradeAssetBalanceOptions {
  /** The asset whose balance is shown; a change while a request is pending invalidates it. */
  readonly asset: Ref<string>;
  /** The chain the balance is read on. */
  readonly chain: Ref<string>;
  /** The connected address the balance belongs to. */
  readonly address: Readonly<Ref<string | undefined>>;
  /** Cleared on every refresh: an amount entered against the previous balance is meaningless. */
  readonly amount: Ref<string>;
  /** Set aside from the balance when working out what can actually be sent. */
  readonly estimatedGasFee: Readonly<Ref<string>>;
  /** While no gas estimate is possible there is nothing to offer as a max. */
  readonly gasEstimable: Readonly<Ref<boolean>>;
}

interface UseTradeAssetBalanceReturn {
  readonly assetBalance: Readonly<Ref<BigNumber | undefined>>;
  readonly max: Readonly<Ref<string>>;
  readonly refreshAssetBalance: () => Promise<void>;
  readonly resetMax: () => void;
}

/**
 * The connected address's balance of the selected asset, and the amount of it that can actually be
 * sent once gas is set aside.
 *
 * Like the gas estimate this is racy - the response is dropped when the asset changed while the
 * request was in flight, so a slow answer for a previous asset cannot land as the current balance.
 */
export function useTradeAssetBalance(options: UseTradeAssetBalanceOptions): UseTradeAssetBalanceReturn {
  const { address, amount, asset, chain, estimatedGasFee, gasEstimable } = options;

  const assetBalance = shallowRef<BigNumber>();
  const max = shallowRef<string>('0');

  const { getEvmChainName } = useSupportedChains();
  const { getAssetBalance } = useTradeApi();

  function resetMax(): void {
    set(max, '0');
  }

  async function refreshAssetBalance(): Promise<void> {
    set(amount, '');
    set(assetBalance, undefined);

    const currentChain = get(chain);
    const currentAsset = get(asset);
    const currentAddress = get(address);

    if (!currentChain || !currentAsset || !currentAddress)
      return;

    const evmChain = getEvmChainName(currentChain);

    if (!evmChain)
      return;

    const payload: GetAssetBalancePayload = {
      address: currentAddress,
      asset: currentAsset,
      evmChain,
    };

    try {
      const response = await getAssetBalance(payload);
      // Dropped when the selection moved on while the request was in flight.
      if (get(asset) === payload.asset)
        set(assetBalance, response);
    }
    catch (error) {
      logger.error(error);
    }
  }

  watch([chain, asset, address], async () => {
    await refreshAssetBalance();
  });

  watch([estimatedGasFee, assetBalance], () => {
    set(max, maxSendableAmount(get(assetBalance), get(estimatedGasFee)));
  });

  watchImmediate(gasEstimable, (estimable) => {
    if (!estimable)
      resetMax();
  });

  return {
    // A computed rather than readonly(): deep-readonly would strip BigNumber's own type.
    assetBalance: computed<BigNumber | undefined>(() => get(assetBalance)),
    max: readonly(max),
    refreshAssetBalance,
    resetMax,
  };
}
