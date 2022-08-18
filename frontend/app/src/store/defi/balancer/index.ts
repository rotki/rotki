import {
  BalancerBalances,
  BalancerBalanceWithOwner,
  BalancerEvent,
  BalancerEvents,
  BalancerProfitLoss,
  Pool
} from '@rotki/common/lib/defi/balancer';
import { computed, ComputedRef, ref, Ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { getPremium, useModules } from '@/composables/session';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import { dexTradeNumericKeys } from '@/store/defi/const';
import { DexTrades } from '@/store/defi/types';
import { OnError } from '@/store/typing';
import {
  fetchDataAsync,
  filterAddresses,
  getStatusUpdater
} from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useBalancerStore = defineStore('defi/balancer', () => {
  const events: Ref<BalancerEvents> = ref({});
  const trades: Ref<DexTrades> = ref({});
  const balances: Ref<BalancerBalances> = ref({});

  const { fetchSupportedAssets, assetSymbol } = useAssetInfoRetrieval();
  const { activeModules } = useModules();
  const isPremium = getPremium();

  const addresses = computed(() => Object.keys(get(balances)));

  const balanceList = computed(() => {
    const result: BalancerBalanceWithOwner[] = [];
    const perAddressBalances = get(balances);
    for (const address in perAddressBalances) {
      for (const balance of perAddressBalances[address]) {
        result.push({
          ...balance,
          owner: address
        });
      }
    }
    return result;
  });

  const pools = computed(() => {
    const pools: Record<string, Pool> = {};
    const events = get(eventList());
    const balances = get(balanceList);

    for (const { address, tokens } of balances) {
      if (pools[address]) {
        continue;
      }
      const name = tokens.map(token => get(assetSymbol(token.token))).join('/');
      pools[address] = {
        name: name,
        address: address
      };
    }

    for (const event of events) {
      const pool = event.pool;
      if (!pool || pools[pool.address]) {
        continue;
      }
      pools[pool.address] = {
        name: pool.name,
        address: pool.address
      };
    }
    return Object.values(pools);
  });

  const profitLoss = (addresses: string[] = []) =>
    computed(() => {
      const balancerProfitLoss: Record<string, BalancerProfitLoss> = {};
      filterAddresses(get(events), addresses, item => {
        for (let i = 0; i < item.length; i++) {
          const entry = item[i];
          if (!balancerProfitLoss[entry.poolAddress]) {
            const name = entry.poolTokens
              .map(token => get(assetSymbol(token.token)))
              .join('/');
            balancerProfitLoss[entry.poolAddress] = {
              pool: {
                address: entry.poolAddress,
                name: name
              },
              tokens: entry.poolTokens.map(token => token.token),
              profitLossAmount: entry.profitLossAmounts,
              usdProfitLoss: entry.usdProfitLoss
            };
          }
        }
      });
      return Object.values(balancerProfitLoss);
    });

  const eventList = (addresses: string[] = []): ComputedRef<BalancerEvent[]> =>
    computed(() => {
      const result: BalancerEvent[] = [];
      const perAddressEvents = get(events);
      filterAddresses(perAddressEvents, addresses, item => {
        for (let i = 0; i < item.length; i++) {
          const poolDetail = item[i];
          const name = poolDetail.poolTokens
            .map(pool => get(assetSymbol(pool.token)))
            .join('/');
          result.push(
            ...poolDetail.events.map(value => ({
              ...value,
              pool: {
                name: name,
                address: poolDetail.poolAddress
              }
            }))
          );
        }
      });
      return result;
    });

  const fetchBalances = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_balances.task.title').toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.balancer_balances.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.balancer_balances.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.BALANCER_BALANCES,
          section: Section.DEFI_BALANCER_BALANCES,
          query: async () => await api.defi.fetchBalancerBalances(),
          parser: data => BalancerBalances.parse(data),
          meta,
          onError
        },
        requires: {
          premium: true,
          module: Module.BALANCER
        },
        state: {
          isPremium,
          activeModules: activeModules as Ref<string[]>
        },
        refresh
      },
      balances
    );

    await fetchSupportedAssets(true);
  };

  const fetchTrades = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_trades.task.title').toString(),
      numericKeys: dexTradeNumericKeys
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.balancer_trades.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.balancer_trades.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.BALANCER_TRADES,
          section: Section.DEFI_BALANCER_TRADES,
          query: async () => await api.defi.fetchBalancerTrades(),
          meta: meta,
          onError: onError
        },
        requires: {
          module: Module.BALANCER,
          premium: true
        },
        state: {
          isPremium,
          activeModules: activeModules as Ref<string[]>
        },

        refresh
      },
      trades
    );

    await fetchSupportedAssets(true);
  };
  const fetchEvents = async (refresh: boolean = false) => {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_events.task.title').toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.balancer_events.error.title').toString(),
      error: message => {
        return i18n
          .t('actions.defi.balancer_events.error.description', {
            message
          })
          .toString();
      }
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.BALANCER_EVENT,
          section: Section.DEFI_BALANCER_EVENTS,
          query: async () => await api.defi.fetchBalancerEvents(),
          parser: data => BalancerEvents.parse(data),
          meta: meta,
          onError: onError
        },
        requires: {
          premium: true,
          module: Module.BALANCER
        },
        state: {
          isPremium,
          activeModules: activeModules as Ref<string[]>
        },
        refresh
      },
      events
    );

    await fetchSupportedAssets(true);
  };

  const reset = () => {
    const { resetStatus } = getStatusUpdater(Section.DEFI_BALANCER_BALANCES);
    set(balances, {});
    set(events, {});
    set(trades, {});
    resetStatus(Section.DEFI_BALANCER_BALANCES);
    resetStatus(Section.DEFI_BALANCER_TRADES);
    resetStatus(Section.DEFI_BALANCER_EVENTS);
  };

  return {
    events,
    trades,
    balances,
    addresses,
    pools,
    balanceList,
    eventList,
    profitLoss,
    fetchBalances,
    fetchTrades,
    fetchEvents,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBalancerStore, import.meta.hot));
}
