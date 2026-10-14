import type { ComputedRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import { useAssetStatisticState } from '@/modules/settings/use-asset-statistic-state';
import { useSettingModel } from '@/modules/settings/use-setting-model';

type SourcePreference = 'events' | 'snapshot';

interface UseAssetBalanceSourceSettingReturn {
  name: ComputedRef<string>;
  rememberStateForAsset: WritableComputedRef<boolean>;
  modelUseHistoricalAssetBalances: Ref<boolean, boolean>;
  persistSource: (value: boolean | undefined) => Promise<void>;
}

/**
 * Where the asset graph reads its balances from: snapshots or history events, globally or
 * remembered per asset. Reports an asset's remembered choice through `onPreference` whenever the
 * asset or the choice changes, menu open or not, so it lives with the always-mounted activator.
 */
export function useAssetBalanceSourceSetting(
  asset: MaybeRefOrGetter<string | undefined>,
  onPreference: (preference?: SourcePreference) => void,
  enabled: MaybeRefOrGetter<boolean> = true,
): UseAssetBalanceSourceSettingReturn {
  const {
    getPreference,
    name,
    rememberStateForAsset,
    suppressIfPerAsset,
    modelUseHistoricalAssetBalances,
  } = useAssetStatisticState(asset);

  const { model } = useSettingModel('useHistoricalAssetBalances');

  async function persistSource(value: boolean | undefined): Promise<void> {
    await suppressIfPerAsset(async () => {
      set(model, value ?? false);
    });
  }

  function reportPreference(): void {
    const assetValue = toValue(asset);
    if (!toValue(enabled) || !assetValue || !get(rememberStateForAsset))
      return;

    onPreference(getPreference(assetValue));
  }

  watch(modelUseHistoricalAssetBalances, reportPreference);
  watchImmediate(() => toValue(asset), reportPreference);

  return {
    modelUseHistoricalAssetBalances,
    name,
    persistSource,
    rememberStateForAsset,
  };
}
