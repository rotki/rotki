import type { BigNumber } from '@rotki/common';
import type { DeepReadonly, MaybeRefOrGetter, Ref, ShallowRef } from 'vue';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { bigNumberifyFromRef } from '@/modules/core/common/data/bignumbers';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { useSetting } from '@/modules/settings/use-setting';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

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
  modelAssetToFiatPrice: ShallowRef<string>;
  currencySymbol: DeepReadonly<Ref<string>>;
  fetchedAssetToFiatPrice: Readonly<ShallowRef<string>>;
  fetching: Ref<boolean>;
  modelFiatValue: ShallowRef<string>;
  modelFiatValueFocused: ShallowRef<boolean>;
  reset: () => void;
}

export function useEventPriceConversion({
  amount,
  asset,
  showPriceFields,
  timestamp,
}: UseEventPriceConversionOptions): UseEventPriceConversionReturn {
  const modelFiatValue = shallowRef<string>('');
  const modelAssetToFiatPrice = shallowRef<string>('');
  const modelFiatValueFocused = shallowRef<boolean>(false);
  const fetchedAssetToFiatPrice = shallowRef<string>('');

  const { useIsActivePrefix } = useTaskCenter();
  const { getHistoricPrice } = usePriceTaskManager();
  const currencySymbol = useSetting('currencySymbol');

  const fetching = useIsActivePrefix(ActivityKind.PRICES, ActivityPart.HISTORIC);

  const numericAssetToFiatPrice = bigNumberifyFromRef(modelAssetToFiatPrice);
  const numericFiatValue = bigNumberifyFromRef(modelFiatValue);
  const numericAmount = bigNumberifyFromRef(amount);

  function onAssetToFiatPriceChanged(forceUpdate = false): void {
    if (get(amount) && get(modelAssetToFiatPrice) && (!get(modelFiatValueFocused) || forceUpdate))
      set(modelFiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
  }

  function onFiatValueChange(): void {
    if (get(amount) && get(modelFiatValueFocused))
      set(modelAssetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());
  }

  async function fetchHistoricPrices(): Promise<void> {
    const time = toValue(timestamp);
    const assetVal = get(asset);
    if (!time || !assetVal) {
      // There is nothing to price, so the fields have to be cleared rather than left showing the
      // last asset's number. The parent used to do this by reaching in through a template ref once
      // its own reset had run.
      reset();
      return;
    }

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
    set(modelAssetToFiatPrice, price);
    onAssetToFiatPriceChanged(true);
  });

  watch(modelAssetToFiatPrice, () => {
    onAssetToFiatPriceChanged();
  });

  watch(modelFiatValue, () => {
    onFiatValueChange();
  });

  watch(amount, () => {
    onAssetToFiatPriceChanged();
    onFiatValueChange();
  });

  function reset(): void {
    set(fetchedAssetToFiatPrice, '');
    set(modelAssetToFiatPrice, '');
    set(modelFiatValue, '');
  }

  return {
    modelAssetToFiatPrice,
    currencySymbol,
    fetchedAssetToFiatPrice: readonly(fetchedAssetToFiatPrice),
    fetching,
    modelFiatValue,
    modelFiatValueFocused,
    reset,
  };
}
