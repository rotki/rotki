import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { computed, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section, Status } from '@/store/const';
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
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { getStatus, isLoading, setStatus, useStore } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';

export const useUniswap = defineStore('defi/uniswap', () => {
  const balances = ref<XswapBalances>({}) as Ref<XswapBalances>;
  const trades = ref<DexTrades>({}) as Ref<DexTrades>;
  const events = ref<XswapEvents>({}) as Ref<XswapEvents>;

  const store = useStore();
  const { fetchSupportedAssets } = useAssetInfoRetrieval();

  const uniswapBalances = (addresses: string[]) =>
    computed(() => {
      return getBalances(get(balances), addresses);
    });

  const uniswapPoolProfit = (addresses: string[]) =>
    computed(() => {
      return getPoolProfit(get(events), addresses);
    });

  const uniswapEvents = (addresses: string[]) =>
    computed(() => {
      return getEventDetails(get(events), addresses);
    });

  const addresses = computed(() => {
    const uniswapBalances = get(balances);
    const uniswapEvents = get(events);
    return Object.keys(uniswapBalances)
      .concat(Object.keys(uniswapEvents))
      .filter(uniqueStrings);
  });

  const poolAssets = computed(() => {
    const uniswapBalances = get(balances);
    const uniswapEvents = get(events);
    return getPools(uniswapBalances, uniswapEvents);
  });

  const fetchBalances = async (refresh: boolean = false) => {
    const session = store.state.session!;
    const { activeModules } = session.generalSettings;
    if (!activeModules.includes(Module.UNISWAP)) {
      return;
    }

    const section = Section.DEFI_UNISWAP_BALANCES;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_UNISWAP_BALANCES;
      const { taskId } = await api.defi.fetchUniswapBalances();
      const { result } = await awaitTask<XswapBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.uniswap.task.title'),
          numericKeys: uniswapNumericKeys
        }
      );

      set(balances, result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.uniswap.error.title'),
        message: i18n.tc('actions.defi.uniswap.error.description', undefined, {
          error: e.message
        }),
        display: true
      });
    }
    setStatus(Status.LOADED, section);

    await fetchSupportedAssets(true);
  };

  const fetchTrades = async (refresh: boolean = false) => {
    const session = store.state.session!;
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.UNISWAP) || !session!.premium) {
      return;
    }

    const section = Section.DEFI_UNISWAP_TRADES;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_UNISWAP_TRADES;
      const { taskId } = await api.defi.fetchUniswapTrades();
      const { result } = await awaitTask<DexTrades, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.uniswap_trades.task.title'),
          numericKeys: dexTradeNumericKeys
        }
      );

      set(trades, result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.uniswap_trades.error.title'),
        message: i18n.tc(
          'actions.defi.uniswap_trades.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        display: true
      });
    }
    setStatus(Status.LOADED, section);

    await fetchSupportedAssets(true);
  };

  const fetchEvents = async (refresh: boolean = false) => {
    const session = store.state.session!;
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.UNISWAP) || !session!.premium) {
      return;
    }

    const section = Section.DEFI_UNISWAP_EVENTS;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_UNISWAP_EVENTS;
      const { taskId } = await api.defi.fetchUniswapEvents();
      const { result } = await awaitTask<XswapEvents, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.uniswap_events.task.title'),
          numericKeys: uniswapEventsNumericKeys
        }
      );

      set(events, result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.uniswap_events.error.title'),
        message: i18n.tc(
          'actions.defi.uniswap_events.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        display: true
      });
    }
    setStatus(Status.LOADED, section);

    await fetchSupportedAssets(true);
  };

  return {
    balances,
    trades,
    events,
    addresses,
    poolAssets,
    uniswapEvents,
    uniswapBalances,
    uniswapPoolProfit,
    fetchBalances,
    fetchTrades,
    fetchEvents
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useUniswap, import.meta.hot));
}
