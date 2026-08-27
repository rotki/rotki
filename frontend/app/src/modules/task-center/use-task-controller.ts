import type { Result } from 'plainfp/result';
import type { ControlError } from './core/orchestrator/errors';
import type { Activity, ActivityKind, GroupId } from './core/types';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { useTaskCenter } from './use-task-center';
import { useTaskOrchestrator } from './use-task-orchestrator';

type CommandResult = Result<void, ControlError | TaskError>;

interface UseTaskControllerReturn {
  cancel: (activity: Activity) => Promise<CommandResult>;
  cancelGroup: (group: GroupId) => Promise<void>;
  cancelByKind: (kind: ActivityKind) => Promise<void>;
  cancelAll: () => Promise<void>;
  rerun: (activity: Activity) => CommandResult;
}

/**
 * Offers uniform cancel and rerun control over every activity.
 *
 * @remarks
 * The orchestrator owns them all, so both commands are a lookup by id, and it is the orchestrator
 * that rejects an activity which cannot be cancelled or rerun. Both return a plainfp
 * {@link Result} so callers render failures without try/catch.
 */
export function useTaskController(): UseTaskControllerReturn {
  const orchestrator = useTaskOrchestrator();
  const { model } = useTaskCenter();

  async function cancel(activity: Activity): Promise<CommandResult> {
    return orchestrator.cancel(activity.id);
  }

  function rerun(activity: Activity): CommandResult {
    return orchestrator.rerun(activity.id);
  }

  async function cancelMatching(predicate: (activity: Activity) => boolean): Promise<void> {
    const targets = get(model).groups.flatMap(group => group.activities).filter(predicate);
    await Promise.allSettled(targets.map(async activity => cancel(activity)));
  }

  return {
    cancel,
    cancelAll: async (): Promise<void> => cancelMatching(activity => activity.cancellable),
    cancelByKind: async (kind: ActivityKind): Promise<void> => cancelMatching(activity => activity.kind === kind),
    cancelGroup: async (group: GroupId): Promise<void> => cancelMatching(activity => activity.group === group),
    rerun,
  };
}
