import type { MaybeRef } from 'vue';
import type {
  NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  NonFungibleBalancesRequestPayload,
} from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/common/collection';
import type { TaskMeta } from '@/modules/tasks/types';
import { useNftBalancesApi } from '@/composables/api/balances/nft';
import { useStatusUpdater } from '@/composables/status';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { mapCollectionResponse } from '@/modules/common/data/collection-utils';
import { logger } from '@/modules/common/logging/logging';
import { Module } from '@/modules/common/modules';
import { Section, Status } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';

interface NftBalancesReturn {
  fetchNonFungibleBalances: (payload: MaybeRef<NonFungibleBalancesRequestPayload>) => Promise<Collection<NonFungibleBalance>>;
  refreshNonFungibleBalances: (userInitiated?: boolean) => Promise<void>;
}

export function useNftBalances(): NftBalancesReturn {
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchNfBalances, fetchNfBalancesTask } = useNftBalancesApi();

  const fetchNonFungibleBalances = async (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>,
  ): Promise<Collection<NonFungibleBalance>> => {
    const payloadVal = get(payload);
    const result = await fetchNfBalances(get(payloadVal));

    if (!payloadVal.ignoredAssetsHandling || payloadVal.ignoredAssetsHandling === 'exclude')
      set(nonFungibleTotalValue, result.totalValue);

    return mapCollectionResponse(result);
  };

  const syncNonFungiblesTask = async (): Promise<void> => {
    const defaults: NonFungibleBalancesRequestPayload = {
      ascending: [true],
      ignoreCache: true,
      limit: 0,
      offset: 0,
      orderByAttributes: ['name'],
    };

    const outcome = await runTask<NonFungibleBalancesCollectionResponse, TaskMeta>(
      async () => fetchNfBalancesTask(defaults),
      { type: TaskType.NF_BALANCES, meta: { title: t('actions.nft_balances.task.title') } },
    );

    if (isActionableFailure(outcome)) {
      notifyError(
        t('actions.nft_balances.error.title'),
        t('actions.nft_balances.error.message', {
          message: outcome.message,
        }),
      );
      throw new Error(outcome.message);
    }
  };

  const refreshNonFungibleBalances = async (userInitiated = false): Promise<void> => {
    if (!get(activeModules).includes(Module.NFTS))
      return;

    const { fetchDisabled, isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping non fungible balances refresh');
      return;
    }

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
      await syncNonFungiblesTask();
      setStatus(Status.LOADED);
    }
    catch (error: unknown) {
      logger.error(error);
      resetStatus();
    }
  };

  return {
    fetchNonFungibleBalances,
    refreshNonFungibleBalances,
  };
}
