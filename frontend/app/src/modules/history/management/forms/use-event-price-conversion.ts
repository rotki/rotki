import type { BigNumber } from '@rotki/common';
import type { DeepReadonly, MaybeRefOrGetter, Ref, ShallowRef } from 'vue';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { bigNumberifyFromRef } from '@/modules/core/common/data/bignumbers';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

interface UseEventPriceConversionOptions {
  /** The amount of the asset being priced */
  amount: Ref<string>;
  /** The asset identifier to fetch the price for */
  asset: Ref<string | undefined>;
  /** Whether the price fields are currently visible */
  showPriceFields: Ref<boolean>;
  /** The event timestamp in milliseconds */
  timestamp: MaybeRefOrGetter<number>;
}

interface UseEventPriceConversionReturn {
  assetToFiatPrice: ShallowRef<string>;
  currencySymbol: DeepReadonly<Ref<string>>;
  fetchedAssetToFiatPrice: Readonly<ShallowRef<string>>;
  fetching: Ref<boolean>;
  fiatValue: ShallowRef<string>;
  fiatValueFocused: ShallowRef<boolean>;
  reset: () => void;
}

export function useEventPriceConversion({
  amount,
  asset,
  showPriceFields,
  timestamp,
}: UseEventPriceConversionOptions): UseEventPriceConversionReturn {
  const fiatValue = shallowRef<string>('');
  const assetToFiatPrice = shallowRef<string>('');
  const fiatValueFocused = shallowRef<boolean>(false);
  const fetchedAssetToFiatPrice = shallowRef<string>('');

  const { useIsTaskRunning } = useTaskStore();
  const { getHistoricPrice } = usePriceTaskManager();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  const fetching = useIsTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

  const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
  const numericFiatValue = bigNumberifyFromRef(fiatValue);
  const numericAmount = bigNumberifyFromRef(amount);

  function onAssetToFiatPriceChanged(forceUpdate = false): void {
    if (get(amount) && get(assetToFiatPrice) && (!get(fiatValueFocused) || forceUpdate))
      set(fiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
  }

  function onFiatValueChange(): void {
    if (get(amount) && get(fiatValueFocused))
      set(assetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());
  }

  async function fetchHistoricPrices(): Promise<void> {
    const time = toValue(timestamp);
    const assetVal = get(asset);
    if (!time || !assetVal)
      return;

    const price: BigNumber = await getHistoricPrice({
      fromAsset: assetVal,
      timestamp: millisecondsToSeconds(time),
      toAsset: get(currencySymbol),
    });

    if (price.gte(0))
      set(fetchedAssetToFiatPrice, price.toFixed());
  }

  watchImmediate(
    [(): number => toValue(timestamp), asset, showPriceFields],
    async ([ts, ast, show], [oldTs, oldAst, oldShow]): Promise<void> => {
      if (ts !== oldTs || ast !== oldAst || (oldShow && !show))
        await fetchHistoricPrices();
    },
  );

  watch(fetchedAssetToFiatPrice, (price) => {
    set(assetToFiatPrice, price);
    onAssetToFiatPriceChanged(true);
  });

  watch(assetToFiatPrice, () => {
    onAssetToFiatPriceChanged();
  });

  watch(fiatValue, () => {
    onFiatValueChange();
  });

  watch(amount, () => {
    onAssetToFiatPriceChanged();
    onFiatValueChange();
  });

  function reset(): void {
    set(fetchedAssetToFiatPrice, '');
    set(assetToFiatPrice, '');
    set(fiatValue, '');
  }

  return {
    assetToFiatPrice,
    currencySymbol,
    fetchedAssetToFiatPrice: readonly(fetchedAssetToFiatPrice),
    fetching,
    fiatValue,
    fiatValueFocused,
    reset,
  };
}
