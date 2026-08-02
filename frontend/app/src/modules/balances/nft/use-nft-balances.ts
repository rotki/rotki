import type { MaybeRef } from 'vue';
import type {
  NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  NonFungibleBalancesRequestPayload,
} from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import { map as mapResult, type Result } from 'plainfp/result';
import { useNftBalancesApi } from '@/modules/balances/api/use-nft-balances-api';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface NftBalancesReturn {
  fetchNonFungibleBalances: (payload: MaybeRef<NonFungibleBalancesRequestPayload>) => Promise<Collection<NonFungibleBalance>>;
  refreshNonFungibleBalances: (userInitiated?: boolean) => Promise<void>;
}

export function useNftBalances(): NftBalancesReturn {
  const activeModules = useSetting('activeModules');
  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { statusOf, submitTask } = useNativeTask();
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

  const refreshNonFungibleBalances = async (userInitiated = false): Promise<void> => {
    if (!get(activeModules).includes(Module.NFTS))
      return;

    // `fetchDisabled(refresh)` was `!(isFirstLoad || refresh) || loading`; on the orchestrator's
    // projection that is `(everCompleted && !userInitiated) || active`.
    const status = statusOf(ActivityKind.NFT_BALANCES);
    if ((status.everCompleted && !userInitiated) || status.active) {
      logger.info('skipping non fungible balances refresh');
      return;
    }

    const defaults: NonFungibleBalancesRequestPayload = {
      ascending: [true],
      ignoreCache: true,
      limit: 0,
      offset: 0,
      orderByAttributes: ['name'],
    };

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.NFT_BALANCES),
      kind: ActivityKind.NFT_BALANCES,
      rerunnable: true,
      staleAfter: [
        // A hand-edited price changes what NFTs are worth. Scoped to `prices:manual:*` so the
        // automatic price sweeps do not keep re-running this expensive query.
        { kind: ActivityKind.PRICES, parts: [ActivityPart.MANUAL] },
        // Enabling the module makes these fetchable where they were not before.
        { kind: ActivityKind.MODULE_TOGGLE, parts: [Module.NFTS, 'enabled'] },
      ],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<NonFungibleBalancesCollectionResponse>(
          async () => fetchNfBalancesTask(defaults),
        ),
        () => {},
      ),
      title: t('task_center.group.nft_balances'),
    });

    // Previously this threw and the caller reset the status; the orchestrator now owns the
    // terminal state, so surfacing the error is all that is left to do.
    onActionableError(outcome, (error) => {
      logger.error(error.message);
      notifyError(
        t('actions.nft_balances.error.title'),
        t('actions.nft_balances.error.message', { message: error.message }),
      );
    });
  };

  return {
    fetchNonFungibleBalances,
    refreshNonFungibleBalances,
  };
}
