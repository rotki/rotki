import { type AssetBalance, type BalanceByLocation, BalanceType, type LocationBalance } from '@/types/balances';
import {
  type ManualBalance,
  type ManualBalanceRequestPayload,
  type ManualBalanceWithPrice,
  type ManualBalanceWithValue,
  ManualBalances,
  type RawManualBalance,
} from '@/types/manual-balances';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AssetPrices } from '@/types/prices';
import type { TaskMeta } from '@/types/task';
import type { ActionStatus } from '@/types/action';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';

export const useManualBalancesStore = defineStore('balances/manual', () => {
  const manualBalancesData = ref<ManualBalanceWithValue[]>([]);

  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();
  const { awaitTask } = useTaskStore();
  const { assetPrice } = useBalancePricesStore();
  const { queryManualBalances, addManualBalances, editManualBalances, deleteManualBalances } = useManualBalancesApi();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

  const manualBalances = computed<ManualBalanceWithValue[]>(() =>
    get(manualBalancesData).filter(x => x.balanceType === BalanceType.ASSET),
  );

  const manualLiabilities = computed<ManualBalanceWithValue[]>(() =>
    get(manualBalancesData).filter(x => x.balanceType === BalanceType.LIABILITY),
  );

  const manualLabels = computed<string[]>(() => get(manualBalancesData).map(x => x.label));

  const manualBalanceByLocation = computed<LocationBalance[]>(() => {
    const balances = get(manualBalances);

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: BalanceByLocation = balances.reduce((
      acc: BalanceByLocation,
      balance: LocationBalance,
    ) => {
      if (acc[balance.location]) {
        // if the location exists on the reduced object, add the value of the current item to the previous total
        acc[balance.location] = acc[balance.location].plus(balance.value);
      }
      else {
        // otherwise create the location and initiate its value
        acc[balance.location] = balance.value;
      }

      return acc;
    }, {});

    return Object.keys(aggregateManualBalancesByLocation)
      .map(location => ({
        location,
        value: aggregateManualBalancesByLocation[location],
      }))
      .sort((a, b) => sortDesc(a.value, b.value));
  });

  const getBreakdown = (asset: string, isLiability = false): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() => {
    const breakdown: AssetBreakdown[] = [];
    const balances = isLiability ? get(manualLiabilities) : get(manualBalances);

    for (const balance of balances) {
      const associatedAsset = get(getAssociatedAssetIdentifier(balance.asset));
      if (associatedAsset !== asset)
        continue;

      breakdown.push({
        address: '',
        location: balance.location,
        amount: balance.amount,
        value: balance.value,
        tags: balance.tags ?? undefined,
      });
    }
    return breakdown;
  });

  const assetBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => getBreakdown(asset);
  const liabilityBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => getBreakdown(asset, true);

  const getLocationBreakdown = (id: string): ComputedRef<Record<string, AssetBalance>> => computed<Record<string, AssetBalance>>(() => {
    const assets: Record<string, AssetBalance> = {};
    const balances = get(manualBalances);
    for (const balance of balances) {
      if (balance.location !== id)
        continue;

      appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
    }
    return assets;
  });

  const { getStatus, setStatus, resetStatus, fetchDisabled } = useStatusUpdater(Section.MANUAL_BALANCES);

  const fetchManualBalances = async (userInitiated = false): Promise<void> => {
    if (fetchDisabled(userInitiated)) {
      logger.debug('skipping manual balance refresh');
      return;
    }
    const currentStatus: Status = getStatus();

    const newStatus = currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await queryManualBalances();
      const { result } = await awaitTask<ManualBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.manual_balances.fetch.task.title'),
      });

      const { balances } = ManualBalances.parse(result);
      set(manualBalancesData, balances);
      setStatus(Status.LOADED);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          title: t('actions.balances.manual_balances.error.title'),
          message: t('actions.balances.manual_balances.error.message', {
            message: error.message,
          }),
          display: true,
        });
      }
      resetStatus();
    }
  };

  const addManualBalance = async (balance: RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> => {
    try {
      const taskType = TaskType.MANUAL_BALANCES_ADD;
      const { taskId } = await addManualBalances([balance]);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.manual_balances.add.task.title'),
      });
      const { balances } = ManualBalances.parse(result);
      set(manualBalancesData, balances);
      return {
        success: true,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      let messages = error.message;
      if (error instanceof ApiValidationError)
        messages = error.getValidationErrors(balance);

      return {
        success: false,
        message: messages,
      };
    }
  };

  const editManualBalance = async (balance: ManualBalance): Promise<ActionStatus<ValidationErrors | string>> => {
    try {
      const taskType = TaskType.MANUAL_BALANCES_EDIT;
      const { taskId } = await editManualBalances([balance]);
      const { result } = await awaitTask<ManualBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.manual_balances.edit.task.title'),
      });
      const { balances } = ManualBalances.parse(result);
      set(manualBalancesData, balances);
      return {
        success: true,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      let message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(balance);

      return {
        success: false,
        message,
      };
    }
  };

  const save = async (balance: ManualBalance | RawManualBalance): Promise<ActionStatus<ValidationErrors | string>> =>
    'identifier' in balance ? editManualBalance(balance) : addManualBalance(balance);

  const deleteManualBalance = async (id: number): Promise<void> => {
    try {
      const { balances } = await deleteManualBalances([id]);
      set(manualBalancesData, balances);
    }
    catch (error: any) {
      setMessage({
        title: t('actions.balances.manual_delete.error.title'),
        description: error.message,
      });
    }
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const newManualBalancesData = get(manualBalancesData).map((item) => {
      const assetPrice = get(prices)[item.asset];
      if (!assetPrice)
        return item;

      return {
        ...item,
        value: item.amount.times(assetPrice.value),
      } satisfies ManualBalanceWithValue;
    });

    set(manualBalancesData, newManualBalancesData);
  };

  const resolvers = {
    /**
     * Resolves the asset price in the selected currency.
     * We use this to make sure that total is not affected by double conversion problems.
     *
     * @param asset The asset for which we want the price
     */
    resolveAssetPrice(asset: string): BigNumber | undefined {
      return get(assetPrice(asset));
    },
  };

  const fetchLiabilities = async (
    payload: MaybeRef<ManualBalanceRequestPayload>,
  ): Promise<Collection<ManualBalanceWithPrice>> =>
    Promise.resolve(sortAndFilterManualBalance(get(manualLiabilities), get(payload), resolvers));

  const fetchBalances = async (payload: MaybeRef<ManualBalanceRequestPayload>): Promise<Collection<ManualBalanceWithPrice>> =>
    Promise.resolve(sortAndFilterManualBalance(get(manualBalances), get(payload), resolvers));

  return {
    manualBalancesData,
    manualBalances,
    manualLiabilities,
    manualLabels,
    manualBalanceByLocation,
    assetBreakdown,
    liabilityBreakdown,
    getLocationBreakdown,
    fetchManualBalances,
    addManualBalance,
    editManualBalance,
    deleteManualBalance,
    updatePrices,
    fetchLiabilities,
    fetchBalances,
    save,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useManualBalancesStore, import.meta.hot));
