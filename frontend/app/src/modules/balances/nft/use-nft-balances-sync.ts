import type {
  NonFungibleBalancesCollectionResponse,
  NonFungibleBalancesRequestPayload,
} from '@/modules/balances/types/nfbalances';
import { map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { manualPriceAddActivity } from '@/modules/assets/prices/prices.activity';
import { useNftBalancesApi } from '@/modules/balances/api/use-nft-balances-api';
import { nftBalancesActivity } from '@/modules/balances/balances.activity';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { moduleToggleActivity } from '@/modules/settings/modules/module-toggle.activity';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseNftBalancesSyncReturn {
  syncNonFungibleBalances: () => Promise<void>;
}

/**
 * Submits the backend refresh of the non-fungible balances to the task center.
 */
export function useNftBalancesSync(): UseNftBalancesSyncReturn {
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchNfBalancesTask } = useNftBalancesApi();

  /**
   * Runs the refresh as a rerunnable activity and logs an actionable failure.
   *
   * @remarks
   * Only two things make it stale: a hand-edited price, since that changes what an NFT is worth, and
   * enabling the module, which makes these fetchable where they were not before. The price trigger
   * is scoped to manual edits alone, so the automatic sweeps do not keep re-running this.
   */
  const syncNonFungibleBalances = async (): Promise<void> => {
    const defaults: NonFungibleBalancesRequestPayload = {
      ascending: [true],
      ignoreCache: true,
      limit: 0,
      offset: 0,
      orderByAttributes: ['name'],
    };

    const outcome = await submitTask({
      id: nftBalancesActivity.id(),
      kind: nftBalancesActivity.kind,
      rerunnable: true,
      staleAfter: [
        { kind: manualPriceAddActivity.kind, parts: manualPriceAddActivity.partsWithin([]) },
        { kind: moduleToggleActivity.kind, parts: moduleToggleActivity.partsOf({ enabled: true, module: Module.NFTS }) },
      ],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<NonFungibleBalancesCollectionResponse>(
          async () => fetchNfBalancesTask(defaults),
        ),
        () => {},
      ),
      title: t('task_center.group.nft_balances'),
    });

    onActionableError(outcome, error => logger.error(error.message));
  };

  return { syncNonFungibleBalances };
}
