import { type BigNumber } from '@rotki/common';
import { type MaybeRef } from '@vueuse/core';
import {
  type AssetBalances,
  type BalanceByLocation,
  BalanceType,
  type LocationBalance
} from '@/types/balances';
import {
  type ManualBalance,
  type ManualBalanceWithValue,
  ManualBalances
} from '@/types/manual-balances';
import { type AssetPrices } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type ActionStatus } from '@/types/action';
import { type AssetBreakdown } from '@/types/blockchain/accounts';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const useManualBalancesStore = defineStore('balances/manual', () => {
  const manualBalancesData: Ref<ManualBalanceWithValue[]> = ref([]);

  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();
  const { awaitTask } = useTaskStore();
  const { exchangeRate } = useBalancePricesStore();
  const {
    queryManualBalances,
    addManualBalances,
    editManualBalances,
    deleteManualBalances
  } = useManualBalancesApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

  const manualBalances: ComputedRef<ManualBalanceWithValue[]> = computed(() =>
    get(manualBalancesData).filter(x => x.balanceType === BalanceType.ASSET)
  );

  const manualLiabilities: ComputedRef<ManualBalanceWithValue[]> = computed(
    () =>
      get(manualBalancesData).filter(
        x => x.balanceType === BalanceType.LIABILITY
      )
  );

  const manualLabels = computed<string[]>(() =>
    get(manualBalancesData).map(x => x.label)
  );

  const manualBalanceByLocation: ComputedRef<LocationBalance[]> = computed(
    () => {
      const mainCurrency = get(currencySymbol);
      const balances = get(manualBalances);
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
    }
  );

  const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
    computed(() => {
      const breakdown: AssetBreakdown[] = [];
      const balances = get(manualBalances);

      for (const balance of balances) {
        const associatedAsset = get(
          getAssociatedAssetIdentifier(balance.asset)
        );
        if (associatedAsset !== asset) {
          continue;
        }
        breakdown.push({
          address: '',
          location: balance.location,
          balance: {
            amount: balance.amount,
            usdValue: balance.usdValue
          },
          tags: balance.tags
        });
      }
      return breakdown;
    });

  const getLocationBreakdown = (id: string): ComputedRef<AssetBalances> =>
    computed(() => {
      const assets: AssetBalances = {};
      const balances = get(manualBalances);
      for (const balance of balances) {
        if (balance.location !== id) {
          continue;
        }
        appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
      }
      return assets;
    });

  const fetchManualBalances = async (): Promise<void> => {
    const { getStatus, setStatus, resetStatus } = useStatusUpdater(
      Section.MANUAL_BALANCES
    );
    const currentStatus: Status = getStatus();

    const newStatus =
      currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await queryManualBalances();
      const { result } = await awaitTask<ManualBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.manual_balances.fetch.task.title')
        }
      );

      const { balances } = ManualBalances.parse(result);
      set(manualBalancesData, balances);
      setStatus(Status.LOADED);
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.balances.manual_balances.error.title'),
        message: t('actions.balances.manual_balances.error.message', {
          message: e.message
        }),
        display: true
      });
      resetStatus();
    }
  };

  const addManualBalance = async (
    balance: Omit<ManualBalance, 'id'>
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    try {
      const taskType = TaskType.MANUAL_BALANCES_ADD;
      const { taskId } = await addManualBalances([balance]);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.manual_balances.add.task.title')
        }
      );
      const { balances } = ManualBalances.parse(result);
      set(manualBalancesData, balances);
      return {
        success: true
      };
    } catch (e: any) {
      logger.error(e);

      let messages = e.message;
      if (e instanceof ApiValidationError) {
        messages = e.getValidationErrors(balance);
      }
      return {
        success: false,
        message: messages
      };
    }
  };

  const editManualBalance = async (
    balance: ManualBalance
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    try {
      const taskType = TaskType.MANUAL_BALANCES_EDIT;
      const { taskId } = await editManualBalances([balance]);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.manual_balances.edit.task.title')
        }
      );
      const { balances } = ManualBalances.parse(result);
      set(manualBalancesData, balances);
      return {
        success: true
      };
    } catch (e: any) {
      logger.error(e);

      let message = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors(balance);
      }
      return {
        success: false,
        message
      };
    }
  };

  const deleteManualBalance = async (id: number): Promise<void> => {
    try {
      const { balances } = await deleteManualBalances([id]);
      set(manualBalancesData, balances);
    } catch (e: any) {
      setMessage({
        title: t('actions.balances.manual_delete.error.title').toString(),
        description: e.message
      });
    }
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const newManualBalancesData = get(manualBalancesData).map(item => {
      const assetPrice = get(prices)[item.asset];
      if (!assetPrice) {
        return item;
      }
      return {
        ...item,
        usdValue: item.amount.times(assetPrice.usdPrice ?? assetPrice.value)
      };
    });

    set(manualBalancesData, newManualBalancesData);
  };

  return {
    manualBalancesData,
    manualBalances,
    manualLiabilities,
    manualLabels,
    manualBalanceByLocation,
    getBreakdown,
    getLocationBreakdown,
    fetchManualBalances,
    addManualBalance,
    editManualBalance,
    deleteManualBalance,
    updatePrices
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useManualBalancesStore, import.meta.hot)
  );
}
