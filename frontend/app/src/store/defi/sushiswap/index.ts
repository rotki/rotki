import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { computed, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { getPremium, useModules } from '@/composables/session';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import {
  dexTradeNumericKeys,
  uniswapEventsNumericKeys,
  uniswapNumericKeys
} from '@/store/defi/const';
import { DexTrades } from '@/store/defi/types';
import {
  getBalances,
  getEventDetails,
  getPoolProfit,
  getPools
} from '@/store/defi/xswap-utils';
import { OnError } from '@/store/typing';
import { fetchDataAsync, getStatusUpdater } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';

export const useSushiswapStore = defineStore('defi/sushiswap', () => {
  const balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const events = ref<XswapEvents>({});
  const trades = ref<DexTrades>({});

  const isPremium = getPremium();
  const { activeModules } = useModules();
  const { fetchSupportedAssets } = useAssetInfoRetrieval();

  const balanceList = (addresses: string[]) =>
    computed(() => getBalances(get(balances), addresses, false));
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
      title: i18n.t('actions.defi.sushiswap_balances.task.title').toString(),
      numericKeys: uniswapNumericKeys
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.sushiswap_balances.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.sushiswap_balances.error.description', {
            message
          })
          .toString()
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

    await fetchSupportedAssets(true);
  }

  async function fetchTrades(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.sushiswap_trades.task.title').toString(),
      numericKeys: dexTradeNumericKeys
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.sushiswap_trades.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.sushiswap_trades.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.SUSHISWAP_TRADES,
          section: Section.DEFI_SUSHISWAP_TRADES,
          meta,
          query: async () => await api.defi.fetchSushiswapTrades(),
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
      trades
    );

    await fetchSupportedAssets(true);
  }

  async function fetchEvents(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.sushiswap_events.task.title').toString(),
      numericKeys: uniswapEventsNumericKeys
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.sushiswap_events.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.sushiswap_events.error.description', {
            message
          })
          .toString()
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

    await fetchSupportedAssets(true);
  }

  async function reset() {
    const { resetStatus } = getStatusUpdater(Section.DEFI_SUSHISWAP_BALANCES);
    set(balances, {});
    set(events, {});
    resetStatus();
    resetStatus(Section.DEFI_SUSHISWAP_EVENTS);
  }

  return {
    balances,
    events,
    trades,
    addresses,
    pools,
    balanceList,
    eventList,
    poolProfit,
    fetchBalances,
    fetchTrades,
    fetchEvents,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSushiswapStore, import.meta.hot));
}
