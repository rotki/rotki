import { type XswapBalance, XswapBalances, XswapEvents, type XswapPoolProfit } from '@rotki/common';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { getBalances, getPoolProfit, getPools } from '@/utils/defi/xswap';
import { fetchDataAsync } from '@/utils/fetch-async';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useUniswapApi } from '@/composables/api/defi/uniswap';
import { useStatusUpdater } from '@/composables/status';
import { usePremium } from '@/composables/premium';
import type { TaskMeta } from '@/types/task';
import type { OnError } from '@/types/fetch';

export const useUniswapStore = defineStore('defi/uniswap', () => {
  const v2Balances = ref<XswapBalances>({});
  const events = ref<XswapEvents>({});

  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const isPremium = usePremium();
  const { t } = useI18n();

  const { fetchUniswapEvents, fetchUniswapV2Balances } = useUniswapApi();

  const uniswapV2Balances = (addresses: string[]): ComputedRef<XswapBalance[]> =>
    computed(() => getBalances(get(v2Balances), addresses));

  const uniswapPoolProfit = (addresses: string[]): ComputedRef<XswapPoolProfit[]> =>
    computed(() => getPoolProfit(get(events), addresses));

  const uniswapV2Addresses = computed(() => {
    const uniswapBalances = get(v2Balances);
    const uniswapEvents = get(events);
    return Object.keys(uniswapBalances).concat(Object.keys(uniswapEvents)).filter(uniqueStrings);
  });

  const uniswapV2PoolAssets = computed(() => {
    const uniswapBalances = get(v2Balances);
    const uniswapEvents = get(events);
    return getPools(uniswapBalances, uniswapEvents);
  });

  const fetchV2Balances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.uniswap.task.title', { v: 2 }),
    };

    const onError: OnError = {
      error: message => t('actions.defi.uniswap.error.description', {
        error: message,
        v: 2,
      }),
      title: t('actions.defi.uniswap.error.title', { v: 2 }),
    };

    await fetchDataAsync(
      {
        refresh,
        requires: {
          module: Module.UNISWAP,
          premium: false,
        },
        state: {
          activeModules,
          isPremium,
        },
        task: {
          meta,
          onError,
          parser: data => XswapBalances.parse(data),
          query: async () => fetchUniswapV2Balances(),
          section: Section.DEFI_UNISWAP_V2_BALANCES,
          type: TaskType.DEFI_UNISWAP_V2_BALANCES,
        },
      },
      v2Balances,
    );
  };

  const fetchEvents = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.uniswap_events.task.title'),
    };

    const onError: OnError = {
      error: message =>
        t('actions.defi.uniswap_events.error.description', {
          error: message,
        }),
      title: t('actions.defi.uniswap_events.error.title'),
    };

    await fetchDataAsync(
      {
        refresh,
        requires: {
          module: Module.UNISWAP,
          premium: true,
        },
        state: {
          activeModules,
          isPremium,
        },
        task: {
          meta,
          onError,
          parser: data => XswapEvents.parse(data),
          query: async () => fetchUniswapEvents(),
          section: Section.DEFI_UNISWAP_EVENTS,
          type: TaskType.DEFI_UNISWAP_EVENTS,
        },
      },
      events,
    );
  };

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_UNISWAP_V2_BALANCES);
    set(v2Balances, {});
    set(events, {});

    resetStatus({ section: Section.DEFI_UNISWAP_V2_BALANCES });
    resetStatus({ section: Section.DEFI_UNISWAP_EVENTS });
  };

  return {
    events,
    fetchEvents,
    fetchV2Balances,
    reset,
    uniswapPoolProfit,
    uniswapV2Addresses,
    uniswapV2Balances,
    uniswapV2PoolAssets,
    v2Balances,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useUniswapStore, import.meta.hot));
