import {
  type BalancerBalance,
  BalancerBalances,
  type BalancerEvent,
  BalancerEvents,
  type BalancerProfitLoss
} from '@rotki/common/lib/defi/balancer';
import { type XswapPool } from '@rotki/common/lib/defi/xswap';
import cloneDeep from 'lodash/cloneDeep';
import { type ComputedRef, type Ref } from 'vue';
import { type Writeable } from '@/types';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type OnError } from '@/types/fetch';

export const useBalancerStore = defineStore('defi/balancer', () => {
  const events: Ref<BalancerEvents> = ref({});
  const balances: Ref<BalancerBalances> = ref({});

  const { activeModules } = useModules();
  const isPremium = usePremium();
  const { t } = useI18n();
  const { fetchBalancerBalances, fetchBalancerEvents } = useBalancerApi();

  const addresses = computed(() => Object.keys(get(balances)));

  const balancerBalances = (addresses: string[]) =>
    computed<BalancerBalance[]>(() => {
      const perAddressBalances = get(balances);

      const aggregatedBalances: Record<string, Writeable<BalancerBalance>> = {};

      for (const account in perAddressBalances) {
        if (addresses.length > 0 && !addresses.includes(account)) {
          continue;
        }
        const accountBalances = cloneDeep(perAddressBalances)[account];
        if (!accountBalances || accountBalances.length === 0) {
          continue;
        }

        for (const {
          address,
          tokens,
          totalAmount,
          userBalance
        } of accountBalances) {
          const balance = aggregatedBalances[address];
          if (balance) {
            const oldBalance = balance.userBalance;
            balance.userBalance = balanceSum(oldBalance, userBalance);

            tokens.forEach(token => {
              const index = balance.tokens.findIndex(
                item => item.token === token.token
              );
              if (index > -1) {
                const existingAssetData = balance.tokens[index];
                const userBalance = balanceSum(
                  existingAssetData.userBalance,
                  token.userBalance
                );
                balance.tokens[index] = {
                  ...existingAssetData,
                  userBalance
                };
              } else {
                balance.tokens.push(token);
              }
            });
          } else {
            aggregatedBalances[address] = {
              address,
              tokens,
              totalAmount,
              userBalance
            };
          }
        }
      }

      return Object.values(aggregatedBalances);
    });

  const pools = computed(() => {
    const pools: Record<string, XswapPool> = {};
    const events = get(eventList());
    const balances = get(balancerBalances([]));

    for (const { address, tokens } of balances) {
      if (pools[address]) {
        continue;
      }
      const assets = tokens.map(token => token.token);
      pools[address] = {
        assets,
        address
      };
    }

    for (const event of events) {
      const pool = event.pool;
      if (!pool || pools[pool.address]) {
        continue;
      }
      pools[pool.address] = {
        assets: pool.assets,
        address: pool.address
      };
    }
    return Object.values(pools);
  });

  const profitLoss = (addresses: string[] = []) =>
    computed(() => {
      const balancerProfitLoss: Record<string, BalancerProfitLoss> = {};
      filterAddresses(get(events), addresses, item => {
        for (const entry of item) {
          if (!balancerProfitLoss[entry.poolAddress]) {
            const assets = entry.poolTokens.map(token => token.token);
            balancerProfitLoss[entry.poolAddress] = {
              pool: {
                address: entry.poolAddress,
                assets
              },
              tokens: assets,
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
        for (const poolDetail of item) {
          const assets = poolDetail.poolTokens.map(pool => pool.token);
          result.push(
            ...poolDetail.events.map(value => ({
              ...value,
              pool: {
                assets,
                address: poolDetail.poolAddress
              }
            }))
          );
        }
      });
      return result;
    });

  const fetchBalances = async (refresh = false) => {
    const meta: TaskMeta = {
      title: t('actions.defi.balancer_balances.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.balancer_balances.error.title').toString(),
      error: message =>
        t('actions.defi.balancer_balances.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.BALANCER_BALANCES,
          section: Section.DEFI_BALANCER_BALANCES,
          query: async () => await fetchBalancerBalances(),
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
          activeModules
        },
        refresh
      },
      balances
    );
  };

  const fetchEvents = async (refresh = false) => {
    const meta: TaskMeta = {
      title: t('actions.defi.balancer_events.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.balancer_events.error.title').toString(),
      error: message =>
        t('actions.defi.balancer_events.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.BALANCER_EVENT,
          section: Section.DEFI_BALANCER_EVENTS,
          query: async () => await fetchBalancerEvents(),
          parser: data => BalancerEvents.parse(data),
          meta,
          onError
        },
        requires: {
          premium: true,
          module: Module.BALANCER
        },
        state: {
          isPremium,
          activeModules
        },
        refresh
      },
      events
    );
  };

  const reset = () => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_BALANCER_BALANCES);
    set(balances, {});
    set(events, {});
    resetStatus(Section.DEFI_BALANCER_BALANCES);
    resetStatus(Section.DEFI_BALANCER_EVENTS);
  };

  return {
    events,
    balances,
    addresses,
    pools,
    balancerBalances,
    eventList,
    profitLoss,
    fetchBalances,
    fetchEvents,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBalancerStore, import.meta.hot));
}
