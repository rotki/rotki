import {
  type XswapBalance,
  XswapBalances,
  type XswapEventDetails,
  XswapEvents,
  type XswapPoolProfit
} from '@rotki/common/lib/defi/xswap';
import { type ComputedRef, type Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useStatusUpdater } from '@/composables/status';
import { api } from '@/services/rotkehlchen-api';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/store/defi/xswap-utils';
import { type OnError } from '@/store/typing';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { fetchDataAsync } from '@/utils/fetch-async';

export const useSushiswapStore = defineStore('defi/sushiswap', () => {
  const balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const events = ref<XswapEvents>({});

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t } = useI18n();

  const balanceList = (addresses: string[]): ComputedRef<XswapBalance[]> =>
    computed(() => getBalances(get(balances), addresses));
  const poolProfit = (addresses: string[]): ComputedRef<XswapPoolProfit[]> =>
    computed(() => getPoolProfit(get(events) as XswapEvents, addresses));
  const eventList = (addresses: string[]): ComputedRef<XswapEventDetails[]> =>
    computed(() => getEventDetails(get(events) as XswapEvents, addresses));
  const addresses = computed(() =>
    Object.keys(get(balances)).concat(
      Object.keys(get(events)).filter(uniqueStrings)
    )
  );
  const pools = computed(() =>
    getPools(get(balances), get(events) as XswapEvents)
  );

  const fetchBalances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.sushiswap_balances.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.sushiswap_balances.error.title').toString(),
      error: message =>
        t('actions.defi.sushiswap_balances.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.SUSHISWAP_BALANCES,
          section: Section.DEFI_SUSHISWAP_BALANCES,
          meta,
          query: async () => await api.defi.fetchSushiswapBalances(),
          parser: XswapBalances.parse,
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: true,
          module: Module.SUSHISWAP
        },
        refresh
      },
      balances
    );
  };

  const fetchEvents = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.sushiswap_events.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.sushiswap_events.error.title').toString(),
      error: message =>
        t('actions.defi.sushiswap_events.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.SUSHISWAP_EVENTS,
          section: Section.DEFI_SUSHISWAP_EVENTS,
          meta,
          query: async () => await api.defi.fetchSushiswapEvents(),
          parser: XswapEvents.parse,
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          module: Module.SUSHISWAP,
          premium: true
        },
        refresh
      },
      events
    );
  };

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_SUSHISWAP_BALANCES);
    set(balances, {});
    set(events, {});
    resetStatus();
    resetStatus(Section.DEFI_SUSHISWAP_EVENTS);
  };

  return {
    balances,
    events,
    addresses,
    pools,
    balanceList,
    eventList,
    poolProfit,
    fetchBalances,
    fetchEvents,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSushiswapStore, import.meta.hot));
}
