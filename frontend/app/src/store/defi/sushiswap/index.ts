import { type XswapBalance, XswapBalances, XswapEvents, type XswapPoolProfit } from '@rotki/common';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { getBalances, getPoolProfit, getPools } from '@/utils/defi/xswap';
import { fetchDataAsync } from '@/utils/fetch-async';
import { useSushiswapApi } from '@/composables/api/defi/sushiswap';
import { useStatusUpdater } from '@/composables/status';
import { useModules } from '@/composables/session/modules';
import { usePremium } from '@/composables/premium';
import type { TaskMeta } from '@/types/task';
import type { OnError } from '@/types/fetch';

export const useSushiswapStore = defineStore('defi/sushiswap', () => {
  const balances = ref<XswapBalances>({});
  const events = ref<XswapEvents>({});

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t } = useI18n();
  const { fetchSushiswapBalances, fetchSushiswapEvents } = useSushiswapApi();

  const balanceList = (addresses: string[]): ComputedRef<XswapBalance[]> =>
    computed(() => getBalances(get(balances), addresses));
  const poolProfit = (addresses: string[]): ComputedRef<XswapPoolProfit[]> =>
    computed(() => getPoolProfit(get(events), addresses));
  const addresses = computed(() => Object.keys(get(balances)).concat(Object.keys(get(events)).filter(uniqueStrings)));
  const pools = computed(() => getPools(get(balances), get(events)));

  const fetchBalances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.sushiswap_balances.task.title'),
    };

    const onError: OnError = {
      error: message => t('actions.defi.sushiswap_balances.error.description', {
        message,
      }),
      title: t('actions.defi.sushiswap_balances.error.title'),
    };

    await fetchDataAsync(
      {
        refresh,
        requires: {
          module: Module.SUSHISWAP,
          premium: true,
        },
        state: {
          activeModules,
          isPremium,
        },
        task: {
          meta,
          onError,
          parser: data => XswapBalances.parse(data),
          query: async () => fetchSushiswapBalances(),
          section: Section.DEFI_SUSHISWAP_BALANCES,
          type: TaskType.SUSHISWAP_BALANCES,
        },
      },
      balances,
    );
  };

  const fetchEvents = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.sushiswap_events.task.title'),
    };

    const onError: OnError = {
      error: message =>
        t('actions.defi.sushiswap_events.error.description', {
          message,
        }),
      title: t('actions.defi.sushiswap_events.error.title'),
    };

    await fetchDataAsync(
      {
        refresh,
        requires: {
          module: Module.SUSHISWAP,
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
          query: async () => fetchSushiswapEvents(),
          section: Section.DEFI_SUSHISWAP_EVENTS,
          type: TaskType.SUSHISWAP_EVENTS,
        },
      },
      events,
    );
  };

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_SUSHISWAP_BALANCES);
    set(balances, {});
    set(events, {});
    resetStatus();
    resetStatus({ section: Section.DEFI_SUSHISWAP_EVENTS });
  };

  return {
    addresses,
    balanceList,
    balances,
    events,
    fetchBalances,
    fetchEvents,
    poolProfit,
    pools,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSushiswapStore, import.meta.hot));
