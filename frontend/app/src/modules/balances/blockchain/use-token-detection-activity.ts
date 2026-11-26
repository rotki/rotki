import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { tokenDetectionActivity } from '@/modules/balances/balances.activity';
import { arrayify } from '@/modules/core/common/data/array';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { activityParts } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseTokenDetectionActivityReturn {
  /**
   * Whether detection is live for a chain, or for one address on it when `address` is given.
   *
   * @remarks
   * Callers need not filter out addresses already detecting: the deterministic activity id dedups
   * a concurrent re-submit.
   */
  isDetectingTokens: (blockchain: string, address: string | null) => boolean;
  useIsDetecting: (chain: MaybeRefOrGetter<string | string[]>, address?: MaybeRefOrGetter<string | null>) => ComputedRef<boolean>;
}

/**
 * Reads token detection liveness off the task center's activities.
 *
 * A detection is live while its activity is pending or running, so this needs no state of its own.
 */
export function useTokenDetectionActivity(): UseTokenDetectionActivityReturn {
  const { activities } = useTaskOrchestrator();

  function isDetectingTokens(blockchain: string, address: string | null): boolean {
    return get(activities).some((activity) => {
      if (activity.kind !== tokenDetectionActivity.kind || isTerminalStatus(activity.status))
        return false;
      const [chain, addr] = activityParts(activity.id);
      return chain === blockchain && (address === null || addr === address);
    });
  }

  const useIsDetecting = (
    chain: MaybeRefOrGetter<string | string[]>,
    address: MaybeRefOrGetter<string | null> = null,
  ): ComputedRef<boolean> => computed<boolean>(() => {
    const addr = toValue(address);
    return arrayify(toValue(chain)).some(blockchain => isDetectingTokens(blockchain, addr));
  });

  return {
    isDetectingTokens,
    useIsDetecting,
  };
}
