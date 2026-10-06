import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import { chunk } from 'es-toolkit';
import { err, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { AssetPriceResponse } from '@/modules/assets/prices/price-types';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { setDigest } from '@/modules/core/common/data/digest';
import { Cancelled, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { type ActivityContext, type RunBackendTask, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseFetchPricesReturn {
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  queryLatestPrices: (context: ActivityContext, payload: FetchPricePayload) => Promise<Result<void, TaskError>>;
}

/**
 * A stable short digest of the requested asset set, for the activity id.
 *
 * `submitTask` dedups by id, so the set has to be part of the identity: under a single
 * `prices:latest` id, opening the manual-balance form while the background sweep was in flight
 * handed the form the sweep's promise, its own batch never ran, and the form showed no price.
 * The set itself cannot go in the id — it is routinely hundreds of assets — so it is folded to
 * FNV-1a/32, sorted first so member order never changes the identity.
 *
 * A collision would re-introduce exactly the bug this prevents, for one pair of sets. At the
 * handful of price requests that can be in flight at once, that is far below the noise floor,
 * and the failure is a stale price rather than a wrong one.
 */
export const assetSetDigest = setDigest;

/**
 * Fetches the latest asset prices as one PRICES activity.
 *
 * @remarks
 * The orchestrator owns the whole batched fetch, meaning it schedules, reports progress, cancels
 * and re-runs it, while each 100-asset batch runs through the `runTask` the activity hands its body.
 * Callers await a `Promise<void>` and read the prices store once it resolves.
 *
 * It keeps no status of its own: liveness ("is it fetching") and freshness ("has it ever loaded")
 * are read off the orchestrator through `useTaskCenter().useWorkStatus(ActivityKind.PRICES)`.
 */
export function useFetchPrices(): UseFetchPricesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { submitTask } = useNativeTask();
  const currencySymbol = useSetting('currencySymbol');
  const { prices } = storeToRefs(useBalancePricesStore());
  const { queryPrices } = usePriceApi();

  /** Query one batch and fold the parsed response into the price store — failures stay errors. */
  const fetchBatch = async (runTask: RunBackendTask, assets: string[], ignoreCache: boolean): Promise<Result<void, TaskError>> => mapResult(
    await runTask<AssetPriceResponse>(
      async () => queryPrices(assets, get(currencySymbol), ignoreCache),
    ),
    (response: AssetPriceResponse) => {
      set(prices, { ...get(prices), ...AssetPriceResponse.parse(response) });
    },
  );

  /**
   * The body of a latest-price fetch: the assets in batches of 100, run inside the activity that
   * `context` belongs to, so an activity that does more than fetch prices can run it as one stage.
   *
   * @remarks
   * Stops at the first failed batch, and between batches once the activity is cancelled: a cancel
   * cannot interrupt the body, and the batches left would otherwise all run after the row already
   * says CANCELLED.
   */
  const queryLatestPrices = async ({ cancelled, report, runTask }: ActivityContext, payload: FetchPricePayload): Promise<Result<void, TaskError>> => {
    const batches = chunk([...payload.selectedAssets], 100);
    const total = batches.length;
    for (const [index, batch] of batches.entries()) {
      if (cancelled())
        return err(Cancelled({ message: 'Cancelled between price batches' }));

      report({ current: index, total });
      const result = await fetchBatch(runTask, batch, payload.ignoreCache);
      if (isErr(result))
        return result;
    }
    report({ current: total, total });
    return ok(undefined);
  };

  const fetchPrices = async (payload: FetchPricePayload): Promise<void> => {
    const selected = [...payload.selectedAssets];
    const assetCount = selected.length;

    if (assetCount === 0)
      return;

    await submitTask({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.LATEST, assetSetDigest(selected), payload.ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED),
      kind: ActivityKind.PRICES,
      rerunnable: true,
      run: async (context): Promise<Result<void, TaskError>> => queryLatestPrices(context, payload),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.latest'), { count: assetCount }, assetCount),
      title: t('task_center.group.prices'),
    });
  };

  return { fetchPrices, queryLatestPrices };
}
