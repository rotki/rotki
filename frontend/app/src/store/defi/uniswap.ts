import { AssetBalance, Balance } from '@rotki/common';
import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { computed, Ref, ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { Section } from '@/store/const';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/store/defi/xswap-utils';
import { fetchDataAsync } from '@/store/fetch-async';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { OnError } from '@/store/typing';
import { uniswapEventsNumericKeys } from '@/types/defi/protocols';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { sortDesc } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

export const useUniswapStore = defineStore('defi/uniswap', () => {
  const v2Balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const v3Balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const events = ref<XswapEvents>({}) as Ref<XswapEvents>;

  const { fetchSupportedAssets } = useAssetInfoRetrieval();
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const isPremium = usePremium();

  const uniswapV2Balances = (addresses: string[]) =>
    computed(() => {
      return getBalances(get(v2Balances), addresses, false);
    });

  const uniswapV3Balances = (addresses: string[]) =>
    computed(() => {
      return getBalances(get(v3Balances), addresses, false);
    });

  const uniswapPoolProfit = (addresses: string[]) =>
    computed(() => {
      return getPoolProfit(get(events), addresses);
    });

  const uniswapEvents = (addresses: string[]) =>
    computed(() => {
      return getEventDetails(get(events), addresses);
    });

  const uniswapV2Addresses = computed(() => {
    const uniswapBalances = get(v2Balances);
    const uniswapEvents = get(events);
    return Object.keys(uniswapBalances)
      .concat(Object.keys(uniswapEvents))
      .filter(uniqueStrings);
  });

  const uniswapV3Addresses = computed(() => {
    const uniswapBalances = get(v3Balances);
    const uniswapEvents = get(events);
    return Object.keys(uniswapBalances)
      .concat(Object.keys(uniswapEvents))
      .filter(uniqueStrings);
  });

  const uniswapV2PoolAssets = computed(() => {
    const uniswapBalances = get(v2Balances);
    const uniswapEvents = get(events);
    return getPools(uniswapBalances, uniswapEvents);
  });

  const uniswapV3PoolAssets = computed(() => {
    const uniswapBalances = get(v3Balances);
    return getPools(uniswapBalances, {});
  });

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { isAssetIgnored } = useIgnoredAssetsStore();

  const uniswapV3AggregatedBalances = (address: string | string[] = []) =>
    computed<AssetBalance[]>(() => {
      const ownedAssets: Record<string, Balance> = {};

      const addToOwned = (value: AssetBalance) => {
        const associatedAsset: string = get(
          getAssociatedAssetIdentifier(value.asset)
        );

        const ownedAsset = ownedAssets[associatedAsset];

        ownedAssets[associatedAsset] = !ownedAsset
          ? {
              ...value
            }
          : {
              ...balanceSum(ownedAsset, value)
            };
      };

      const balances = get(
        uniswapV3Balances(Array.isArray(address) ? address : [address])
      );

      balances.forEach(balance => {
        const assets = balance.assets;
        assets.forEach(asset => {
          addToOwned({
            ...asset.userBalance,
            asset: asset.asset
          });
        });
      });

      return Object.keys(ownedAssets)
        .filter(asset => !get(isAssetIgnored(asset)))
        .map(asset => ({
          asset,
          amount: ownedAssets[asset].amount,
          usdValue: ownedAssets[asset].usdValue
        }))
        .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
    });

  const fetchV2Balances = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.uniswap.task.title', { v: 2 }).toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.uniswap.error.title', { v: 2 }).toString(),
      error: message =>
        i18n
          .t('actions.defi.uniswap.error.description', {
            error: message,
            v: 2
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.DEFI_UNISWAP_V2_BALANCES,
          section: Section.DEFI_UNISWAP_V2_BALANCES,
          meta,
          query: async () => await api.defi.fetchUniswapV2Balances(),
          parser: data => XswapBalances.parse(data),
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: false,
          module: Module.UNISWAP
        },
        refresh
      },
      v2Balances
    );

    await fetchSupportedAssets(true);
  };

  const fetchV3Balances = async (refresh: boolean = false) => {
    const meta = {
      title: i18n.t('actions.defi.uniswap.task.title', { v: 3 }).toString(),
      numericKeys: [],
      premium: get(isPremium)
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.uniswap.error.title', { v: 3 }).toString(),
      error: message =>
        i18n
          .t('actions.defi.uniswap.error.description', {
            error: message,
            v: 3
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.DEFI_UNISWAP_V3_BALANCES,
          section: Section.DEFI_UNISWAP_V3_BALANCES,
          meta,
          query: async () => await api.defi.fetchUniswapV3Balances(),
          parser: data => XswapBalances.parse(data),
          onError,
          checkLoading: { premium: get(isPremium) }
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: false,
          module: Module.UNISWAP
        },
        refresh
      },
      v3Balances
    );

    await fetchSupportedAssets(true);
  };

  const fetchEvents = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: i18n.tc('actions.defi.uniswap_events.task.title'),
      numericKeys: uniswapEventsNumericKeys
    };

    const onError: OnError = {
      title: i18n.tc('actions.defi.uniswap_events.error.title'),
      error: message =>
        i18n.tc('actions.defi.uniswap_events.error.description', undefined, {
          error: message
        })
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.DEFI_UNISWAP_EVENTS,
          section: Section.DEFI_UNISWAP_EVENTS,
          meta,
          query: async () => await api.defi.fetchUniswapEvents(),
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: true,
          module: Module.UNISWAP
        },
        refresh
      },
      events
    );

    await fetchSupportedAssets(true);
  };

  const reset = () => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_UNISWAP_V3_BALANCES);
    set(v2Balances, {});
    set(v3Balances, {});
    set(events, {});

    resetStatus(Section.DEFI_UNISWAP_V2_BALANCES);
    resetStatus(Section.DEFI_UNISWAP_V3_BALANCES);
    resetStatus(Section.DEFI_UNISWAP_EVENTS);
  };

  return {
    v2Balances,
    v3Balances,
    events,
    uniswapV2Addresses,
    uniswapV3Addresses,
    uniswapV2PoolAssets,
    uniswapV3PoolAssets,
    uniswapV2Balances,
    uniswapV3Balances,
    uniswapV3AggregatedBalances,
    uniswapEvents,
    uniswapPoolProfit,
    fetchV2Balances,
    fetchV3Balances,
    fetchEvents,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useUniswapStore, import.meta.hot));
}
