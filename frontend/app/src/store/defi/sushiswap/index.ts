import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { Ref } from 'vue';
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
import { OnError } from '@/store/typing';
import {
  uniswapEventsNumericKeys,
  uniswapNumericKeys
} from '@/types/defi/protocols';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { fetchDataAsync } from '@/utils/fetch-async';

export const useSushiswapStore = defineStore('defi/sushiswap', () => {
  const balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const events = ref<XswapEvents>({});

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t } = useI18n();

  const balanceList = (addresses: string[]) =>
    computed(() => getBalances(get(balances), addresses));
  const poolProfit = (addresses: string[]) =>
    computed(() => getPoolProfit(get(events) as XswapEvents, addresses));
  const eventList = (addresses: string[]) =>
    computed(() => getEventDetails(get(events) as XswapEvents, addresses));
  const addresses = computed(() =>
    Object.keys(get(balances)).concat(
      Object.keys(get(events)).filter(uniqueStrings)
    )
  );
  const pools = computed(() =>
    getPools(get(balances), get(events) as XswapEvents)
  );

  async function fetchBalances(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: t('actions.defi.sushiswap_balances.task.title').toString(),
      numericKeys: uniswapNumericKeys
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
  }

  async function fetchEvents(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: t('actions.defi.sushiswap_events.task.title').toString(),
      numericKeys: uniswapEventsNumericKeys
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
  }

  async function reset() {
    const { resetStatus } = useStatusUpdater(Section.DEFI_SUSHISWAP_BALANCES);
    set(balances, {});
    set(events, {});
    resetStatus();
    resetStatus(Section.DEFI_SUSHISWAP_EVENTS);
  }

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
