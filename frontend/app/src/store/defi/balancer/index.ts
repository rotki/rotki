import { type BalancerBalance, BalancerBalances, type BalancerProfitLoss, type Writeable, type XswapPool } from '@rotki/common';
import { cloneDeep } from 'lodash-es';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { TaskMeta } from '@/types/task';
import type { OnError } from '@/types/fetch';

export const useBalancerStore = defineStore('defi/balancer', () => {
  const balances = ref<BalancerBalances>({});

  const { activeModules } = useModules();
  const isPremium = usePremium();
  const { t } = useI18n();
  const { fetchBalancerBalances } = useBalancerApi();
  const { resetStatus } = useStatusUpdater(Section.DEFI_BALANCER_BALANCES);

  const addresses = computed<string[]>(() => Object.keys(get(balances)));

  const balancerBalances = (addresses: string[]): ComputedRef<BalancerBalance[]> => computed<BalancerBalance[]>(() => {
    const perAddressBalances = get(balances);

    const aggregatedBalances: Record<string, Writeable<BalancerBalance>> = {};

    for (const account in perAddressBalances) {
      if (addresses.length > 0 && !addresses.includes(account))
        continue;

      const accountBalances = cloneDeep(perAddressBalances)[account];
      if (!accountBalances || accountBalances.length === 0)
        continue;

      for (const { address, tokens, totalAmount, userBalance } of accountBalances) {
        const balance = aggregatedBalances[address];
        if (balance) {
          const oldBalance = balance.userBalance;
          balance.userBalance = balanceSum(oldBalance, userBalance);

          tokens.forEach((token) => {
            const index = balance.tokens.findIndex(item => item.token === token.token);
            if (index > -1) {
              const existingAssetData = balance.tokens[index];
              const userBalance = balanceSum(existingAssetData.userBalance, token.userBalance);
              balance.tokens[index] = {
                ...existingAssetData,
                userBalance,
              };
            }
            else {
              balance.tokens.push(token);
            }
          });
        }
        else {
          aggregatedBalances[address] = {
            address,
            tokens,
            totalAmount,
            userBalance,
          };
        }
      }
    }

    return Object.values(aggregatedBalances);
  });

  const pools = computed<XswapPool[]>(() => {
    const pools: Record<string, XswapPool> = {};
    const balances = get(balancerBalances([]));

    for (const { address, tokens } of balances) {
      if (pools[address])
        continue;

      const assets = tokens.map(token => token.token);
      pools[address] = {
        assets,
        address,
      };
    }
    return Object.values(pools);
  });

  /**
   * @deprecated
   * @param _addresses
   * TODO: old pnl was based on the events which we removed because
   */
  const profitLoss = (
    _addresses: string[] = [],
  ): ComputedRef<BalancerProfitLoss[]> => computed<BalancerProfitLoss[]>(() => []);

  const fetchBalances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.balancer_balances.task.title'),
    };

    const onError: OnError = {
      title: t('actions.defi.balancer_balances.error.title'),
      error: message =>
        t('actions.defi.balancer_balances.error.description', {
          message,
        }),
    };

    await fetchDataAsync({
      task: {
        type: TaskType.BALANCER_BALANCES,
        section: Section.DEFI_BALANCER_BALANCES,
        query: async () => await fetchBalancerBalances(),
        parser: data => BalancerBalances.parse(data),
        meta,
        onError,
      },
      requires: {
        premium: true,
        module: Module.BALANCER,
      },
      state: {
        isPremium,
        activeModules,
      },
      refresh,
    }, balances);
  };

  const reset = (): void => {
    set(balances, {});
    resetStatus({ section: Section.DEFI_BALANCER_BALANCES });
  };

  return {
    balances,
    addresses,
    pools,
    balancerBalances,
    profitLoss,
    fetchBalances,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancerStore, import.meta.hot));
