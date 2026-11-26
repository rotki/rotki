import type { OracleCachePayload } from '@/modules/assets/prices/price-types';
import { err, isOk, map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { oracleCacheActivity } from '@/modules/assets/prices/prices.activity';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseOracleCacheTaskReturn {
  /** Reports the outcome as its only message; a cancelled run reports nothing. */
  createOracleCache: (payload: OracleCachePayload) => Promise<Result<void, TaskError>>;
}

/**
 * Builds an oracle's price cache for one pair as a single, non-rerunnable activity.
 *
 * @remarks
 * Only one cache build runs at a time: asking for another while one is active fails at once
 * without submitting anything.
 */
export function useOracleCacheTask(): UseOracleCacheTaskReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { statusOf, submitTask } = useNativeTask();
  const { notifyInfo } = useNotifications();
  const { getAssetField } = useAssetInfoRetrieval();
  const { createPriceCache } = usePriceApi();

  const buildOracleCache = async ({
    fromAsset,
    purgeOld,
    source,
    toAsset,
  }: OracleCachePayload): Promise<Result<void, TaskError>> => {
    if (statusOf(oracleCacheActivity.kind, ...oracleCacheActivity.partsOf()).active)
      return err(TaskFailed({ message: t('actions.balances.create_oracle_cache.already_running') }));

    const cacheTitle = t('actions.balances.create_oracle_cache.task', {
      fromAsset,
      source,
      toAsset,
    });

    return submitTask({
      id: oracleCacheActivity.id(),
      kind: oracleCacheActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<true>(
          async () => createPriceCache(source, fromAsset, toAsset, purgeOld),
        ),
        () => {},
      ),
      subtitle: cacheTitle,
      title: t('task_center.group.prices'),
    });
  };

  const createOracleCache = async (payload: OracleCachePayload): Promise<Result<void, TaskError>> => {
    const outcome = await buildOracleCache(payload);
    const title = t('oracle_prices.cache.notification.title');
    const pair = {
      fromAsset: getAssetField(payload.fromAsset, 'symbol'),
      source: payload.source,
      toAsset: getAssetField(payload.toAsset, 'symbol'),
    };

    if (isOk(outcome))
      notifyInfo(title, t('oracle_prices.cache.notification.success', pair));

    return outcome;
  };

  return {
    createOracleCache,
  };
}
