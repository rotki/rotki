import {
  type XswapBalance,
  XswapBalances,
  type XswapEventDetails,
  XswapEvents,
  type XswapPoolProfit
} from '@rotki/common/lib/defi/xswap';
import { type ComputedRef, type Ref } from 'vue';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/utils/defi/xswap';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { fetchDataAsync } from '@/utils/fetch-async';
import { type OnError } from '@/types/fetch';

export const useSushiswapStore = defineStore('defi/sushiswap', () => {
  const balances: Ref<XswapBalances> = ref<XswapBalances>({});
  const events: Ref<XswapEvents> = ref({});

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t } = useI18n();
  const { fetchSushiswapBalances, fetchSushiswapEvents } = useSushiswapApi();

  const balanceList = (addresses: string[]): ComputedRef<XswapBalance[]> =>
    computed(() => getBalances(get(balances), addresses));
  const poolProfit = (addresses: string[]): ComputedRef<XswapPoolProfit[]> =>
    computed(() => getPoolProfit(get(events), addresses));
  const eventList = (addresses: string[]): ComputedRef<XswapEventDetails[]> =>
    computed(() => getEventDetails(get(events), addresses));
  const addresses = computed(() =>
    Object.keys(get(balances)).concat(
      Object.keys(get(events)).filter(uniqueStrings)
    )
  );
  const pools = computed(() => getPools(get(balances), get(events)));

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
          query: async () => await fetchSushiswapBalances(),
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
          query: async () => await fetchSushiswapEvents(),
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
