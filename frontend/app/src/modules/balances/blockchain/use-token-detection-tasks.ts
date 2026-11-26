import type { Result } from 'plainfp/result';
import type { TaskError } from '@/modules/core/tasks/task-result';
import type { ActivityId } from '@/modules/task-center/core/types';
import { assert } from '@rotki/common';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { tokenDetectionActivity } from '@/modules/balances/balances.activity';
import { useTokenDetectionApi } from '@/modules/balances/blockchain/use-token-detection-api';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseTokenDetectionTasksReturn {
  queueDetectionForChain: (chain: string, addrs: string[], parent?: ActivityId) => Promise<void>;
}

/**
 * Submits token detection to the task center, one activity per address.
 */
export function useTokenDetectionTasks(): UseTokenDetectionTasksReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { detectTokensForAddress } = useTokenDetectionApi();
  const { getChainName, supportsTransactions } = useSupportedChains();
  const { isAddressExcluded } = useDisabledChains();
  const { submitTask } = useNativeTask();

  /**
   * One detection activity per address, resolving when they have all settled.
   *
   * Per-address rather than one activity for the chain, and that is deliberate: `ActivitySteps`
   * is `{ current, total }` and nothing else, so progress can say "3/9" but never *which* address;
   * and `cancel` targets an activity id, so per-account cancel needs per-account activities.
   * Folding them into the chain would delete both capabilities, not defer them.
   *
   * On the per-chain `detect:` family, never {@link BALANCES_LANE}. The chain job that awaits
   * this holds a balances slot for its whole body, so sharing that lane would deadlock it against
   * its own children.
   */
  const queueDetectionForChain = async (chain: string, addrs: string[], parent?: ActivityId): Promise<void> => {
    assert(supportsTransactions(chain));
    const detectable = addrs.filter(addr => !isAddressExcluded(chain, addr));
    if (detectable.length === 0)
      return;

    await Promise.all(detectable.map(async addr => submitTask({
      id: tokenDetectionActivity.id({ address: addr, chain }),
      kind: tokenDetectionActivity.kind,
      lane: tokenDetectionActivity.laneOf?.({ address: addr, chain }),
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => detectTokensForAddress(runTask, chain, addr),
      subtitle: activityLabelFor(msg.$t('task_center.activity.token_detection.detect'), { address: addr, chain: getChainName(chain) }),
      title: t('task_center.group.token_detection'),
    })));
  };

  return { queueDetectionForChain };
}
