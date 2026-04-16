import type { MaybeRef } from 'vue';
import type {
  NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  NonFungibleBalancesRequestPayload,
} from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { useNftBalancesApi } from '@/modules/balances/api/use-nft-balances-api';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { Section, Status } from '@/modules/core/common/status';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

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
