import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import { isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { AssetPriceResponse } from '@/modules/assets/prices/price-types';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { chunkArray } from '@/modules/core/common/data/data';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { type RunBackendTask, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseFetchPricesReturn {
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
}

/**
 * Fetches latest asset prices as a single native PRICES activity (Phase 2 migration). The whole
 * batched fetch is owned by the orchestrator — it schedules, reports progress, cancels and re-runs
 * it — while each 100-asset batch still flows through `runTaskResult`. Callers keep the same
 * `Promise<void>` API and read the prices store once it resolves.
 */
export function useFetchPrices(): UseFetchPricesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const currencySymbol = useSetting('currencySymbol');
  const { prices } = storeToRefs(useBalancePricesStore());
  const { queryPrices } = usePriceApi();

  const fetchPrices = async (payload: FetchPricePayload): Promise<void> => {
    const selected = [...payload.selectedAssets];
    const batches = chunkArray<string>(selected, 100);

    /** Query one batch and fold the parsed response into the price store — failures stay errors. */
    const fetchBatch = async (runTask: RunBackendTask, assets: string[]): Promise<Result<void, TaskError>> => mapResult(
      await runTask<AssetPriceResponse>(
        async () => queryPrices(assets, get(currencySymbol), payload.ignoreCache),
      ),
      (response: AssetPriceResponse) => {
        set(prices, { ...get(prices), ...AssetPriceResponse.parse(response) });
      },
    );

    // No status bookkeeping: submitTask registers the PRICES activity, so liveness ("is it
    // fetching") and freshness ("has it ever loaded") are read off the orchestrator via
    // `useTaskCenter().useWorkStatus(ActivityKind.PRICES)`. The run is a sequential, short-
    // circuiting fold: flatMap drops every later batch on the first error, reporting progress
    // before each step and once more on success.
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.LATEST),
      kind: ActivityKind.PRICES,
      rerunnable: true,
      run: async ({ report, runTask }): Promise<Result<void, TaskError>> => {
        const total = batches.length;
        for (const [index, batch] of batches.entries()) {
          report({ current: index, total });
          const result = await fetchBatch(runTask, batch);
          if (isErr(result))
            return result;
        }
        report({ current: total, total });
        return ok(undefined);
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.latest'), { count: selected.length }, selected.length),
      title: t('task_center.group.prices'),
    });

    onActionableError(outcome, error => notifyError(
      t('actions.session.fetch_prices.error.title'),
      t('actions.session.fetch_prices.error.message', { error: error.message }),
    ));
  };

  return { fetchPrices };
}
