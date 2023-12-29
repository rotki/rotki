import { type BigNumber } from '@rotki/common';
import { type MaybeRef } from '@vueuse/core';
import { type Collection } from '@/types/collection';
import { Module } from '@/types/modules';
import {
  type NonFungibleBalance,
  type NonFungibleBalancesCollectionResponse,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useNonFungibleBalancesStore = defineStore(
  'balances/non-fungible',
  () => {
    const nonFungibleTotalValue = ref<BigNumber>(Zero);

    const { activeModules } = storeToRefs(useGeneralSettingsStore());
    const { awaitTask } = useTaskStore();
    const { notify } = useNotificationsStore();
    const { t } = useI18n();
    const { fetchNfBalances, fetchNfBalancesTask } = useNftBalancesApi();

    const fetchNonFungibleBalances = async (
      payload: MaybeRef<NonFungibleBalancesRequestPayload>
    ): Promise<Collection<NonFungibleBalance>> => {
      const payloadVal = get(payload);
      const result = await fetchNfBalances({
        ...get(payloadVal),
        ignoreCache: false
      });

      if (
        !payloadVal.ignoredAssetsHandling ||
        payloadVal.ignoredAssetsHandling === 'exclude'
      ) {
        set(nonFungibleTotalValue, result.totalUsdValue);
      }
      return mapCollectionResponse(result);
    };

    const syncNonFungiblesTask = async (): Promise<boolean> => {
      const taskType = TaskType.NF_BALANCES;

      const defaults: NonFungibleBalancesRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [true],
        orderByAttributes: ['name'],
        ignoreCache: true
      };

      const { taskId } = await fetchNfBalancesTask(defaults);

      try {
        await awaitTask<NonFungibleBalancesCollectionResponse, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('actions.nft_balances.task.title')
          }
        );
        return true;
      } catch (e: any) {
        if (isTaskCancelled(e)) {
          return false;
        }
        notify({
          title: t('actions.nft_balances.error.title'),
          message: t('actions.nft_balances.error.message', {
            message: e.message
          }),
          display: true
        });
        throw e;
      }
    };

    const refreshNonFungibleBalances = async (
      userInitiated = false
    ): Promise<void> => {
      if (!get(activeModules).includes(Module.NFTS)) {
        return;
      }

      const { setStatus, isFirstLoad, resetStatus, fetchDisabled } =
        useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

      if (fetchDisabled(userInitiated)) {
        logger.info('skipping non fungible balances refresh');
        return;
      }

      try {
        setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
        await syncNonFungiblesTask();
        setStatus(Status.LOADED);
      } catch (e: any) {
        logger.error(e);
        resetStatus();
      }
    };

    return {
      nonFungibleTotalValue,
      fetchNonFungibleBalances,
      refreshNonFungibleBalances
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useNonFungibleBalancesStore, import.meta.hot)
  );
}
