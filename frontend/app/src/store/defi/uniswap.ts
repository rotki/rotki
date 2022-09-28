import {
  XswapBalance,
  XswapBalances,
  XswapEvents
} from '@rotki/common/lib/defi/xswap';
import { ComputedRef, Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { api } from '@/services/rotkehlchen-api';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/store/defi/xswap-utils';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { OnError } from '@/store/typing';
import { uniswapEventsNumericKeys } from '@/types/defi/protocols';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { fetchDataAsync } from '@/utils/fetch-async';

export const useUniswapStore = defineStore('defi/uniswap', () => {
  const v2Balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const v3Balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const events = ref<XswapEvents>({}) as Ref<XswapEvents>;

  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const isPremium = usePremium();
  const { t, tc } = useI18n();

  const uniswapV2Balances = (
    addresses: string[]
  ): ComputedRef<XswapBalance[]> =>
    computed(() => {
      return getBalances(get(v2Balances), addresses);
    });

  const uniswapV3Balances = (
    addresses: string[]
  ): ComputedRef<XswapBalance[]> =>
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

  const fetchV2Balances = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: t('actions.defi.uniswap.task.title', { v: 2 }).toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: t('actions.defi.uniswap.error.title', { v: 2 }).toString(),
      error: message =>
        t('actions.defi.uniswap.error.description', {
          error: message,
          v: 2
        }).toString()
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
  };

  const fetchV3Balances = async (refresh: boolean = false) => {
    const meta = {
      title: t('actions.defi.uniswap.task.title', { v: 3 }).toString(),
      numericKeys: [],
      premium: get(isPremium)
    };

    const onError: OnError = {
      title: t('actions.defi.uniswap.error.title', { v: 3 }).toString(),
      error: message =>
        t('actions.defi.uniswap.error.description', {
          error: message,
          v: 3
        }).toString()
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
  };

  const fetchEvents = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: tc('actions.defi.uniswap_events.task.title'),
      numericKeys: uniswapEventsNumericKeys
    };

    const onError: OnError = {
      title: tc('actions.defi.uniswap_events.error.title'),
      error: message =>
        tc('actions.defi.uniswap_events.error.description', undefined, {
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
