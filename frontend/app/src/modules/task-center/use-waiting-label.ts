import type { ComputedRef } from 'vue';
import { type Activity, type ActivityId, type ActivityWaiting, WaitingReason } from './core/types';
import { useActivityLabel } from './use-activity-label';
import { useTaskCenter } from './use-task-center';

/** Every activity in the model by id, built once for all the rows that name what they wait on. */
const useActivityIndex = createSharedComposable((): ComputedRef<ReadonlyMap<ActivityId, Activity>> => {
  const { model } = useTaskCenter();
  return computed<ReadonlyMap<ActivityId, Activity>>(() => {
    const { children, roots } = get(model);
    const all = [...roots, ...[...children.values()].flat()];
    return new Map(all.map(activity => [activity.id, activity]));
  });
});

interface UseWaitingLabelReturn {
  /** Why a queued activity has not started, or `undefined` for one that is not waiting. */
  waitingLabel: (activity: Activity) => string | undefined;
}

/**
 * Says why a queued activity has not started, naming what it waits on where the reason points at
 * another activity.
 *
 * @remarks
 * A parent or dependency is named the way a nested row would name it, by what it acts on (a chain
 * or an address) before its title. One that has already left the model is not named at all.
 */
export function useWaitingLabel(): UseWaitingLabelReturn {
  const { t } = useI18n({ useScope: 'global' });
  const byId = useActivityIndex();
  const { labelOf } = useActivityLabel();

  function nameOf(waiting: ActivityWaiting): string | undefined {
    const other = waiting.on === undefined ? undefined : get(byId).get(waiting.on);
    return other === undefined ? undefined : labelOf(other, true);
  }

  function waitingLabel(activity: Activity): string | undefined {
    const { waiting } = activity;
    if (waiting === undefined)
      return undefined;

    switch (waiting.reason) {
      case WaitingReason.PARENT:
      case WaitingReason.DEPENDENCY: {
        const name = nameOf(waiting);
        if (name === undefined)
          return t('task_dock.waiting.other_work');
        return waiting.reason === WaitingReason.PARENT
          ? t('task_dock.waiting.parent', { name })
          : t('task_dock.waiting.dependency', { name });
      }
      case WaitingReason.HISTORY_SYNC:
        return t('task_dock.waiting.history_sync');
      case WaitingReason.REDECODE:
        return t('task_dock.waiting.redecode');
      case WaitingReason.MATCHING:
        return t('task_dock.waiting.matching');
      case WaitingReason.SLOT:
        return t('task_dock.waiting.slot');
    }
  }

  return { waitingLabel };
}
