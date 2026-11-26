import { type BigNumber, Blockchain } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, provide, type Ref, shallowRef, toRef, toValue, watch } from 'vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isAmountExceeded, isTradeValid } from '@/modules/wallet/send/trade-send-utils';
import { useTradeAssetBalance } from '@/modules/wallet/send/use-trade-asset-balance';
import { useTradeGasEstimation } from '@/modules/wallet/send/use-trade-gas-estimation';
import { useTradeNetworkMatch } from '@/modules/wallet/send/use-trade-network-match';
import { useTradeRecipientWarning } from '@/modules/wallet/send/use-trade-recipient-warning';
import { TradableAssetKey, useTradableAsset } from '@/modules/wallet/use-tradable-asset';

interface UseTradeSendFormOptions {
  /** The connected address the transfer is sent from and whose holdings are offered. */
  connectedAddress: MaybeRefOrGetter<string | undefined>;
  /** The chains the connected account supports; a selected chain outside them falls back to the first. */
  chainOptions: MaybeRefOrGetter<string[]>;
}

interface UseTradeSendFormReturn {
  /** The amount to send, as typed. */
  amount: Ref<string>;
  /** Whether the amount is more than can be sent. */
  amountExceeded: ComputedRef<boolean>;
  /** The identifier of the asset to send. */
  asset: Ref<string>;
  /** The balance of the asset on the selected chain, unknown until read. */
  assetBalance: Readonly<Ref<BigNumber | undefined>>;
  /** The chain the transfer is made on. */
  assetChain: Ref<string>;
  estimatingGas: Readonly<Ref<boolean>>;
  /** Whether the asset is the native token of the selected chain. */
  isNativeAsset: ComputedRef<boolean>;
  /** The most that can be sent once gas is set aside. */
  max: Readonly<Ref<string>>;
  refreshAssetBalance: () => Promise<void>;
  /** Clears the recipient and the amount, for a fresh transfer. */
  resetInput: () => void;
  showNeverInteractedWarning: Readonly<Ref<boolean>>;
  switchToSelectedChain: () => void;
  /** The recipient address, as typed. */
  toAddress: Ref<string>;
  /** Whether the form holds a transfer that can be sent. */
  valid: ComputedRef<boolean>;
  /** Whether the wallet sits on another chain than the selected one. */
  wrongNetwork: ComputedRef<boolean>;
}

/**
 * The state of the send form: what is sent, where to and on which chain, with the balance, gas
 * and network checks that decide whether it can go.
 *
 * @remarks
 * Provides the tradable asset to the form's children, so it has to be called during setup of the
 * component that renders them.
 */
export function useTradeSendForm(options: UseTradeSendFormOptions): UseTradeSendFormReturn {
  const { chainOptions, connectedAddress } = options;
  const address = toRef(connectedAddress);

  const modelAmount = shallowRef<string>('');
  const modelAsset = shallowRef<string>('');
  const modelAssetChain = shallowRef<string>(Blockchain.ETH);
  const modelToAddress = shallowRef<string>('');

  const { getNativeAsset } = useSupportedChains();

  const { switchToSelectedChain, wrongNetwork } = useTradeNetworkMatch(modelAssetChain);

  const tradableAsset = useTradableAsset(connectedAddress);
  provide(TradableAssetKey, tradableAsset);
  const { getAssetDetail } = tradableAsset;

  const assetDetail = getAssetDetail(modelAsset, modelAssetChain);
  const isAssetResolved = computed<boolean>(() => !!get(assetDetail));

  const isNativeAsset = computed<boolean>(() => {
    const chain = get(modelAssetChain);
    const assetVal = get(modelAsset);
    if (!chain || !assetVal)
      return false;

    return assetVal === getNativeAsset(chain);
  });

  const { showNeverInteractedWarning } = useTradeRecipientWarning({
    fromAddress: address,
    toAddress: modelToAddress,
  });

  const { estimatedGasFee, estimatingGas, gasEstimable } = useTradeGasEstimation({
    asset: modelAsset,
    chain: modelAssetChain,
    isAssetResolved,
    isNativeAsset,
  });

  const { assetBalance, max, refreshAssetBalance, resetMax } = useTradeAssetBalance({
    address,
    amount: modelAmount,
    asset: modelAsset,
    chain: modelAssetChain,
    estimatedGasFee,
    gasEstimable,
  });

  const amountExceeded = computed<boolean>(() => isAmountExceeded(get(modelAmount), get(max)));

  const valid = computed<boolean>(() => isTradeValid(get(modelAmount), get(modelToAddress), get(max)));

  function resetInput(): void {
    set(modelToAddress, '');
    set(modelAmount, '');
    resetMax();
  }

  watch([modelAssetChain, (): string[] => toValue(chainOptions)], ([currentChain, chains]) => {
    if (!chains.includes(currentChain))
      set(modelAssetChain, chains[0]);
  });

  return {
    amount: modelAmount,
    amountExceeded,
    asset: modelAsset,
    assetBalance,
    assetChain: modelAssetChain,
    estimatingGas,
    isNativeAsset,
    max,
    refreshAssetBalance,
    resetInput,
    showNeverInteractedWarning,
    switchToSelectedChain,
    toAddress: modelToAddress,
    valid,
    wrongNetwork,
  };
}
