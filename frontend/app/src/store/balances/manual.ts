import { BigNumber } from '@rotki/common';
import { computed, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import i18n from '@/i18n';
import {
  BalanceType,
  ManualBalance,
  ManualBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { useBalancesStore } from '@/store/balances';
import { useBalancePricesStore } from '@/store/balances/prices';
import { BalanceByLocation, LocationBalance } from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { getStatus, setStatus, showError } from '@/store/utils';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { sortDesc } from '@/utils/bignumbers';

export const useManualBalancesStore = defineStore('balances/manual', () => {
  const manualBalancesData: Ref<ManualBalanceWithValue[]> = ref([]);

  const manualBalances = computed(() => {
    return get(manualBalancesData).filter(
      x => x.balanceType === BalanceType.ASSET
    );
  });

  const manualLiabilities = computed(() => {
    return get(manualBalancesData).filter(
      x => x.balanceType === BalanceType.LIABILITY
    );
  });

  const manualLabels = computed<string[]>(() => {
    return get(manualBalancesData).map(x => x.label);
  });

  const manualBalanceByLocation = computed<LocationBalance[]>(() => {
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const mainCurrency = get(currencySymbol);
    assert(mainCurrency, 'main currency was not properly set');

    const balances = get(manualBalances);
    const { exchangeRate } = useBalancePricesStore();
    const currentExchangeRate = get(exchangeRate(mainCurrency));
    if (currentExchangeRate === undefined) {
      return [];
    }
    const simplifyManualBalances = balances.map(perLocationBalance => {
      // because we mix different assets we need to convert them before they are aggregated
      // thus in amount display we always pass the manualBalanceByLocation in the user's main currency
      let convertedValue: BigNumber;
      if (mainCurrency === perLocationBalance.asset) {
        convertedValue = perLocationBalance.amount as BigNumber;
      } else {
        convertedValue =
          perLocationBalance.usdValue.multipliedBy(currentExchangeRate);
      }

      // to avoid double-conversion, we take as usdValue the amount property when the original asset type and
      // user's main currency coincide
      const { location, usdValue }: LocationBalance = {
        location: perLocationBalance.location,
        usdValue: convertedValue
      };
      return { location, usdValue };
    });

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: BalanceByLocation =
      simplifyManualBalances.reduce(
        (result: BalanceByLocation, manualBalance: LocationBalance) => {
          if (result[manualBalance.location]) {
            // if the location exists on the reduced object, add the usdValue of the current item to the previous total
            result[manualBalance.location] = result[
              manualBalance.location
            ].plus(manualBalance.usdValue);
          } else {
            // otherwise create the location and initiate its value
            result[manualBalance.location] = manualBalance.usdValue;
          }

          return result;
        },
        {}
      );

    return Object.keys(aggregateManualBalancesByLocation)
      .map(location => ({
        location,
        usdValue: aggregateManualBalancesByLocation[location]
      }))
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  });

  const fetchManualBalances = async () => {
    const { awaitTask } = useTasks();
    const currentStatus: Status = getStatus(Section.MANUAL_BALANCES);
    const section = Section.MANUAL_BALANCES;
    const newStatus =
      currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await api.balances.manualBalances();
      const { result } = await awaitTask<ManualBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.manual_balances.task.title'),
          numericKeys: balanceKeys
        }
      );

      set(manualBalancesData, result.balances);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n
          .t('actions.balances.manual_balances.error.title')
          .toString(),
        message: i18n
          .t('actions.balances.manual_balances.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    } finally {
      setStatus(Status.LOADED, section);
    }
  };

  const addManualBalance = async (
    balance: Omit<ManualBalance, 'id'>
  ): Promise<ActionStatus> => {
    try {
      const { balances } = await api.balances.addManualBalances([balance]);
      set(manualBalancesData, balances);
      const { refreshPrices } = useBalancesStore();
      refreshPrices({
        ignoreCache: false,
        selectedAsset: balance.asset
      });
      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const editManualBalance = async (
    balance: ManualBalance
  ): Promise<ActionStatus> => {
    try {
      const { balances } = await api.balances.editManualBalances([balance]);
      set(manualBalancesData, balances);
      const { refreshPrices } = useBalancesStore();
      refreshPrices({
        ignoreCache: false,
        selectedAsset: balance.asset
      });
      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const deleteManualBalance = async (id: number) => {
    try {
      const { balances } = await api.balances.deleteManualBalances([id]);
      set(manualBalancesData, balances);
    } catch (e: any) {
      showError(
        `${e.message}`,
        i18n.t('actions.balances.manual_delete.error.title').toString()
      );
    }
  };

  return {
    manualBalancesData,
    manualBalances,
    manualLiabilities,
    manualLabels,
    manualBalanceByLocation,
    fetchManualBalances,
    addManualBalance,
    editManualBalance,
    deleteManualBalance
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useManualBalancesStore, import.meta.hot)
  );
}
