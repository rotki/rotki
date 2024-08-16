import { type XswapBalance, XswapBalances, XswapEvents, type XswapPoolProfit } from '@rotki/common';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { TaskMeta } from '@/types/task';
import type { OnError } from '@/types/fetch';

export const useUniswapStore = defineStore('defi/uniswap', () => {
  const v2Balances = ref<XswapBalances>({});
  const v3Balances = ref<XswapBalances>({});
  const events = ref<XswapEvents>({});

  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const isPremium = usePremium();
  const { t } = useI18n();

  const { fetchUniswapV2Balances, fetchUniswapV3Balances, fetchUniswapEvents } = useUniswapApi();

  const uniswapV2Balances = (addresses: string[]): ComputedRef<XswapBalance[]> =>
    computed(() => getBalances(get(v2Balances), addresses));

  const uniswapV3Balances = (addresses: string[]): ComputedRef<XswapBalance[]> =>
    computed(() => getBalances(get(v3Balances), addresses, false));

  const uniswapPoolProfit = (addresses: string[]): ComputedRef<XswapPoolProfit[]> =>
    computed(() => getPoolProfit(get(events), addresses));

  const uniswapV2Addresses = computed(() => {
    const uniswapBalances = get(v2Balances);
    const uniswapEvents = get(events);
    return Object.keys(uniswapBalances).concat(Object.keys(uniswapEvents)).filter(uniqueStrings);
  });

  const uniswapV3Addresses = computed(() => {
    const uniswapBalances = get(v3Balances);
    const uniswapEvents = get(events);
    return Object.keys(uniswapBalances).concat(Object.keys(uniswapEvents)).filter(uniqueStrings);
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

  const fetchV2Balances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.uniswap.task.title', { v: 2 }).toString(),
    };

    const onError: OnError = {
      title: t('actions.defi.uniswap.error.title', { v: 2 }).toString(),
      error: message =>
        t('actions.defi.uniswap.error.description', {
          error: message,
          v: 2,
        }).toString(),
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.DEFI_UNISWAP_V2_BALANCES,
          section: Section.DEFI_UNISWAP_V2_BALANCES,
          meta,
          query: async () => await fetchUniswapV2Balances(),
          parser: data => XswapBalances.parse(data),
          onError,
        },
        state: {
          isPremium,
          activeModules,
        },
        requires: {
          premium: false,
          module: Module.UNISWAP,
        },
        refresh,
      },
      v2Balances,
    );
  };

  const fetchV3Balances = async (refresh = false): Promise<void> => {
    const meta = {
      title: t('actions.defi.uniswap.task.title', { v: 3 }).toString(),
      premium: get(isPremium),
    };

    const onError: OnError = {
      title: t('actions.defi.uniswap.error.title', { v: 3 }).toString(),
      error: message =>
        t('actions.defi.uniswap.error.description', {
          error: message,
          v: 3,
        }).toString(),
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.DEFI_UNISWAP_V3_BALANCES,
          section: Section.DEFI_UNISWAP_V3_BALANCES,
          meta,
          query: async () => await fetchUniswapV3Balances(),
          parser: data => XswapBalances.parse(data),
          onError,
          checkLoading: { premium: get(isPremium) },
        },
        state: {
          isPremium,
          activeModules,
        },
        requires: {
          premium: false,
          module: Module.UNISWAP,
        },
        refresh,
      },
      v3Balances,
    );
  };

  const fetchEvents = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.uniswap_events.task.title'),
    };

    const onError: OnError = {
      title: t('actions.defi.uniswap_events.error.title'),
      error: message =>
        t('actions.defi.uniswap_events.error.description', {
          error: message,
        }),
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.DEFI_UNISWAP_EVENTS,
          section: Section.DEFI_UNISWAP_EVENTS,
          meta,
          query: async () => await fetchUniswapEvents(),
          parser: data => XswapEvents.parse(data),
          onError,
        },
        state: {
          isPremium,
          activeModules,
        },
        requires: {
          premium: true,
          module: Module.UNISWAP,
        },
        refresh,
      },
      events,
    );
  };

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_UNISWAP_V3_BALANCES);
    set(v2Balances, {});
    set(v3Balances, {});
    set(events, {});

    resetStatus({ section: Section.DEFI_UNISWAP_V2_BALANCES });
    resetStatus({ section: Section.DEFI_UNISWAP_V3_BALANCES });
    resetStatus({ section: Section.DEFI_UNISWAP_EVENTS });
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
    uniswapPoolProfit,
    fetchV2Balances,
    fetchV3Balances,
    fetchEvents,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useUniswapStore, import.meta.hot));
