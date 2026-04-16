import { omit } from 'es-toolkit';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, type WritableComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { logger } from '@/modules/core/common/logging/logging';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const Source = {
  EVENTS: 'events',
  SNAPSHOT: 'snapshot',
} as const;

export type Source = typeof Source[keyof typeof Source];

enum Preference {
  SNAPSHOT,
  EVENTS,
}

interface UseAssetStatisticsStateReturn {
  getPreference: (asset: string) => Source | undefined;
  name: ComputedRef<string>;
  rememberStateForAsset: WritableComputedRef<boolean>;
  suppressIfPerAsset: (func: () => Promise<void>) => Promise<void>;
  useHistoricalAssetBalances: Ref<boolean, boolean>;
}

export function useAssetStatisticState(asset: MaybeRefOrGetter<string | undefined>): UseAssetStatisticsStateReturn {
  const useHistoricalAssetBalances = ref<boolean>(false);

  const { useHistoricalAssetBalances: enabled } = storeToRefs(useFrontendSettingsStore());

  const { useAssetField } = useAssetInfoRetrieval();
  const stateForAsset = useLocalStorage<Record<string, number>>('rotki.remember-state-for-asset', {});

  const name = useAssetField(asset, 'name');

  const rememberStateForAsset = computed<boolean>({
    get() {
      const assetValue = toValue(asset);
      if (!assetValue) {
        return false;
      }
      return get<Record<string, number>>(stateForAsset)[assetValue] !== undefined;
    },
    set(enabled: boolean) {
      const assetValue = toValue(asset);
      if (!assetValue) {
        return;
      }
      if (enabled) {
        set(stateForAsset, {
          ...get<Record<string, number>>(stateForAsset),
          [assetValue]: get(useHistoricalAssetBalances) ? Preference.EVENTS : Preference.SNAPSHOT,
        });
      }
      else {
        set(stateForAsset, {
          ...omit(get<Record<string, number>>(stateForAsset), [assetValue]),
        });
      }
    },
  });

  function getPreference(asset: string): Source | undefined {
    const assetPreference = get<Record<string, number>>(stateForAsset)[asset];

    if (assetPreference === undefined) {
      return undefined;
    }

    return assetPreference === Preference.EVENTS ? Source.EVENTS : Source.SNAPSHOT;
  }

  async function suppressIfPerAsset(func: () => Promise<void>): Promise<void> {
    if (get(rememberStateForAsset)) {
      logger.debug('tracking only per asset state');
      return;
    }
    await func();
  }

  watch(useHistoricalAssetBalances, (enabled) => {
    const assetValue = toValue(asset);
    if (!(get(rememberStateForAsset)) || !assetValue) {
      return;
    }

    set(stateForAsset, {
      ...get<Record<string, number>>(stateForAsset),
      [assetValue]: enabled ? Preference.EVENTS : Preference.SNAPSHOT,
    });
  });

  watch(() => toValue(asset), (asset) => {
    if (!asset) {
      return;
    }

    if (get(rememberStateForAsset)) {
      set(useHistoricalAssetBalances, get<Record<string, number>>(stateForAsset)[asset] === Preference.EVENTS);
    }
    else {
      set(useHistoricalAssetBalances, get(enabled));
    }
  });

  onMounted(() => {
    set(useHistoricalAssetBalances, get(enabled));
  });

  return {
    getPreference,
    name,
    rememberStateForAsset,
    suppressIfPerAsset,
    useHistoricalAssetBalances,
  };
}
