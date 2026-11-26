import type { Ref } from 'vue';
import type { Module } from '@/modules/core/common/modules';
import { get, set } from '@vueuse/shared';
import { map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { logger } from '@/modules/core/common/logging/logging';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { liquidityPoolsActivity, type LiquidityPoolsPart } from './liquidity-pools.activity';
import { PoolBalances } from './types';

/**
 * The two protocols differ only in module gate, task type, endpoint and target ref, so they
 * share one native submission. Each is a singleton activity (`liquidity-pools:<protocol>`);
 * the old `isTaskRunning || (LOADED && !refresh)` gate becomes the orchestrator's `active` and
 * `everCompleted`.
 */
export interface PoolProtocol {
  readonly module: Module;
  readonly part: LiquidityPoolsPart;
  readonly label: string;
  readonly query: () => Promise<{ taskId: number }>;
  readonly target: Ref<PoolBalances>;
}

interface UsePoolProtocolQueryReturn {
  /**
   * Queries one protocol's pool balances into its target, unless its module is inactive, a query
   * is already running, or one completed and no refresh was asked for.
   */
  retrievePoolBalances: (protocol: PoolProtocol, refresh: boolean) => Promise<void>;
}

/**
 * Submits a liquidity pool protocol's balance query as a task center activity.
 */
export function usePoolProtocolQuery(): UsePoolProtocolQueryReturn {
  const activeModules = useSetting('activeModules');
  const { t } = useI18n({ useScope: 'global' });
  const { statusOf, submitTask } = useNativeTask();

  async function retrievePoolBalances(protocol: PoolProtocol, refresh: boolean): Promise<void> {
    if (!get(activeModules).includes(protocol.module))
      return;

    const status = statusOf(liquidityPoolsActivity.kind, ...liquidityPoolsActivity.partsOf({ part: protocol.part }));
    if (status.active || (status.everCompleted && !refresh))
      return;

    const outcome = await submitTask({
      id: liquidityPoolsActivity.id({ part: protocol.part }),
      kind: liquidityPoolsActivity.kind,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<PoolBalances>(
          async () => protocol.query(),
        ),
        (result) => {
          set(protocol.target, PoolBalances.parse(result));
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.liquidity_pools.protocol'), { protocol: protocol.label }),
      title: t('task_center.group.liquidity_pools'),
    });

    onActionableError(outcome, error => logger.error(`action failure for ${protocol.label}:`, error.message));
  }

  return { retrievePoolBalances };
}
