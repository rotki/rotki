import { type AssetBalances, type BalanceByLocation, BalanceType, type LocationBalance } from '@/types/balances';
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
import { isTaskCancelled } from '@/utils';
import { sortAndFilterManualBalance } from '@/utils/balances/manual/manual-balances';
import { logger } from '@/utils/logging';
import { appendAssetBalance } from '@/utils/balances';
import { sortDesc } from '@/utils/bignumbers';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { useTaskStore } from '@/store/tasks';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusUpdater } from '@/composables/status';
import { useUsdValueThreshold } from '@/composables/usd-value-threshold';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useManualBalancesApi } from '@/composables/api/balances/manual';
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
  const { assetPrice, exchangeRate, isAssetPriceInCurrentCurrency } = useBalancePricesStore();
  const { addManualBalances, deleteManualBalances, editManualBalances, queryManualBalances } = useManualBalancesApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

  const manualBalances = computed<ManualBalanceWithValue[]>(() =>
    get(manualBalancesData).filter(x => x.balanceType === BalanceType.ASSET),
  );

  const manualLiabilities = computed<ManualBalanceWithValue[]>(() =>
    get(manualBalancesData).filter(x => x.balanceType === BalanceType.LIABILITY),
  );

  const manualLabels = computed<string[]>(() => get(manualBalancesData).map(x => x.label));

  const missingCustomAssets = computed<string[]>(() => get(manualBalancesData).filter(item => item.assetIsMissing).map(item => item.asset));

  const manualBalanceByLocation = computed<LocationBalance[]>(() => {
    const mainCurrency = get(currencySymbol);
    const balances = get(manualBalances);
    const currentExchangeRate = get(exchangeRate(mainCurrency));
    if (currentExchangeRate === undefined)
      return [];

    const simplifyManualBalances = balances.map((perLocationBalance) => {
      // because we mix different assets we need to convert them before they are aggregated
      // thus in amount display we always pass the manualBalanceByLocation in the user's main currency
      let convertedValue: BigNumber;
      if (mainCurrency === perLocationBalance.asset)
        convertedValue = perLocationBalance.amount;
      else convertedValue = perLocationBalance.usdValue.multipliedBy(currentExchangeRate);

      // to avoid double-conversion, we take as usdValue the amount property when the original asset type and
      // user's main currency coincide
      const { location, usdValue }: LocationBalance = {
        location: perLocationBalance.location,
        usdValue: convertedValue,
      };
      return { location, usdValue };
    });

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: BalanceByLocation = simplifyManualBalances.reduce(
      (result: BalanceByLocation, manualBalance: LocationBalance) => {
        if (result[manualBalance.location]) {
          // if the location exists on the reduced object, add the usdValue of the current item to the previous total
          result[manualBalance.location] = result[manualBalance.location].plus(manualBalance.usdValue);
        }
        else {
          // otherwise create the location and initiate its value
          result[manualBalance.location] = manualBalance.usdValue;
        }

        return result;
      },
      {},
    );

    return Object.keys(aggregateManualBalancesByLocation)
      .map(location => ({
        location,
        usdValue: aggregateManualBalancesByLocation[location],
      }))
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
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
        amount: balance.amount,
        location: balance.location,
        tags: balance.tags ?? undefined,
        usdValue: balance.usdValue,
      });
    }
    return breakdown;
  });

  const assetBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => getBreakdown(asset);
  const liabilityBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => getBreakdown(asset, true);

  const getLocationBreakdown = (id: string): ComputedRef<AssetBalances> => computed<AssetBalances>(() => {
    const assets: AssetBalances = {};
    const balances = get(manualBalances);
    for (const balance of balances) {
      if (balance.location !== id)
        continue;

      appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
    }
    return assets;
  });

  const { fetchDisabled, getStatus, resetStatus, setStatus } = useStatusUpdater(Section.MANUAL_BALANCES);
  const usdValueThreshold = useUsdValueThreshold(BalanceSource.MANUAL);

  const fetchManualBalances = async (userInitiated = false): Promise<void> => {
    if (fetchDisabled(userInitiated)) {
      logger.debug('skipping manual balance refresh');
      return;
    }
    const currentStatus: Status = getStatus();

    const newStatus = currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    const threshold = get(usdValueThreshold);

    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await queryManualBalances(threshold);
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
          display: true,
          message: t('actions.balances.manual_balances.error.message', {
            message: error.message,
          }),
          title: t('actions.balances.manual_balances.error.title'),
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
        message: messages,
        success: false,
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
        message,
        success: false,
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
        description: error.message,
        title: t('actions.balances.manual_delete.error.title'),
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
        usdValue: item.amount.times(assetPrice.usdPrice ?? assetPrice.value),
      };
    });

    set(manualBalancesData, newManualBalancesData);
  };

  const resolvers: {
    resolveAssetPrice: (asset: string) => BigNumber | undefined;
  } = {
    /**
     * Resolves the asset price in the selected currency.
     * We use this to make sure that total is not affected by double conversion problems.
     *
     * @param asset The asset for which we want the price
     */
    resolveAssetPrice(asset: string): BigNumber | undefined {
      const inCurrentCurrency = get(isAssetPriceInCurrentCurrency(asset));
      const price = get(assetPrice(asset));
      if (!price)
        return undefined;

      if (inCurrentCurrency)
        return price;

      const currentExchangeRate = get(exchangeRate(get(currencySymbol)));

      if (!currentExchangeRate)
        return price;

      return price.times(currentExchangeRate);
    },
  };

  const fetchLiabilities = async (
    payload: MaybeRef<ManualBalanceRequestPayload>,
  ): Promise<Collection<ManualBalanceWithPrice>> =>
    Promise.resolve(sortAndFilterManualBalance(get(manualLiabilities), get(payload), resolvers));

  const fetchBalances = async (payload: MaybeRef<ManualBalanceRequestPayload>): Promise<Collection<ManualBalanceWithPrice>> =>
    Promise.resolve(sortAndFilterManualBalance(get(manualBalances), get(payload), resolvers));

  return {
    addManualBalance,
    assetBreakdown,
    deleteManualBalance,
    editManualBalance,
    fetchBalances,
    fetchLiabilities,
    fetchManualBalances,
    getLocationBreakdown,
    liabilityBreakdown,
    manualBalanceByLocation,
    manualBalances,
    manualBalancesData,
    manualLabels,
    manualLiabilities,
    missingCustomAssets,
    save,
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useManualBalancesStore, import.meta.hot));
