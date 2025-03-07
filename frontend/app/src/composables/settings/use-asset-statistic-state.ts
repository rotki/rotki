import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { logger } from '@/utils/logging';
import { omit } from 'es-toolkit';
import { computed, type ComputedRef, type Ref, type WritableComputedRef } from 'vue';

const Source = {
  EVENTS: 'events',
  SNAPSHOT: 'snapshot',
} as const;

export type Source = typeof Source[keyof typeof Source];

export enum Preference {
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

export function useAssetStatisticState(asset: Ref<string | undefined>): UseAssetStatisticsStateReturn {
  const useHistoricalAssetBalances = ref<boolean>(false);

  const { useHistoricalAssetBalances: enabled } = storeToRefs(useFrontendSettingsStore());

  const { assetName } = useAssetInfoRetrieval();
  const stateForAsset = useLocalStorage<Record<string, number>>('rotki.remember-state-for-asset', {});

  const name = assetName(asset);

  const rememberStateForAsset = computed<boolean>({
    get() {
      if (!isDefined(asset)) {
        return false;
      }
      return get(stateForAsset)[get(asset)] !== undefined;
    },
    set(enabled: boolean) {
      if (!isDefined(asset)) {
        return;
      }
      if (enabled) {
        set(stateForAsset, {
          ...get(stateForAsset),
          [get(asset)]: get(useHistoricalAssetBalances) ? Preference.EVENTS : Preference.SNAPSHOT,
        });
      }
      else {
        set(stateForAsset, {
          ...omit(get(stateForAsset), [get(asset)]),
        });
      }
    },
  });

  function getPreference(asset: string): Source | undefined {
    const assetPreference = get(stateForAsset)[asset];

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
    if (!(get(rememberStateForAsset)) || !isDefined(asset)) {
      return;
    }

    set(stateForAsset, {
      ...get(stateForAsset),
      [get(asset)]: enabled ? Preference.EVENTS : Preference.SNAPSHOT,
    });
  });

  watch(asset, (asset) => {
    if (!asset) {
      return;
    }

    if (get(rememberStateForAsset)) {
      set(useHistoricalAssetBalances, get(stateForAsset)[asset] === Preference.EVENTS);
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
