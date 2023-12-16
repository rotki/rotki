import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import type {
  NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  NonFungibleBalancesRequestPayload,
} from '@/types/nfbalances';
import type { TaskMeta } from '@/types/task';

export const useNonFungibleBalancesStore = defineStore('balances/non-fungible', () => {
  const nonFungibleTotalValue = ref<BigNumber>(Zero);

  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const { fetchNfBalances, fetchNfBalancesTask } = useNftBalancesApi();

  const fetchNonFungibleBalances = async (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>,
  ): Promise<Collection<NonFungibleBalance>> => {
    const payloadVal = get(payload);
    const result = await fetchNfBalances({
      ...get(payloadVal),
      ignoreCache: false,
    });

    if (!payloadVal.ignoredAssetsHandling || payloadVal.ignoredAssetsHandling === 'exclude')
      set(nonFungibleTotalValue, result.totalUsdValue);

    return mapCollectionResponse(result);
  };

  const { isTaskRunning } = useTaskStore();
  const syncNonFungiblesTask = async (): Promise<void> => {
    const taskType = TaskType.NF_BALANCES;
    if (get(isTaskRunning(taskType)))
      return;

    const defaults: NonFungibleBalancesRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [true],
      orderByAttributes: ['name'],
      ignoreCache: true,
    };

    const { taskId } = await fetchNfBalancesTask(defaults);

    try {
      await awaitTask<NonFungibleBalancesCollectionResponse, TaskMeta>(taskId, taskType, {
        title: t('actions.nft_balances.task.title'),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.nft_balances.error.title'),
          message: t('actions.nft_balances.error.message', {
            message: error.message,
          }),
          display: true,
        });
        throw error;
      }
    }
  };

  const refreshNonFungibleBalances = async (userInitiated = false): Promise<void> => {
    if (!get(activeModules).includes(Module.NFTS))
      return;

    const { setStatus, isFirstLoad, resetStatus, fetchDisabled } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping non fungible balances refresh');
      return;
    }

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
      await syncNonFungiblesTask();
      setStatus(Status.LOADED);
    }
    catch (error: any) {
      logger.error(error);
      resetStatus();
    }
  };

  return {
    nonFungibleTotalValue,
    fetchNonFungibleBalances,
    refreshNonFungibleBalances,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useNonFungibleBalancesStore, import.meta.hot));
