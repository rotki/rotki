import type { Ref } from 'vue';
import type { Activity } from './core/types';
import { useSetting } from '@/modules/settings/use-setting';
import { invalidatedKinds } from './core/rerun/policy';
import { isTerminalStatus } from './core/status';
import { type EventMutated, taskCenterBus } from './events/task-center-bus';
import { useTaskCenter } from './use-task-center';
import { useTaskController } from './use-task-controller';

interface UseSmartRerunReturn {
  /** Terminal, rerunnable activities invalidated by an edit and awaiting the user's nod. */
  readonly needsRerun: Readonly<Ref<Activity[]>>;
  /** Re-run everything currently in {@link needsRerun} and clear it. */
  readonly rerunPending: () => void;
  /** Drop the pending suggestions without acting (e.g. user dismissed the prompt). */
  readonly clear: () => void;
}

/**
 * Smart re-run (issue #6825). Listens for `event:mutated` on the task-center bus, maps the edit
 * through the pure {@link invalidatedKinds} policy to the activities it invalidated, then —
 * gated by the `autoRerunOnEdit` frontend setting:
 *  - **on:** re-runs them immediately through the controller.
 *  - **off (default):** collects them into {@link needsRerun} for a later UI prompt.
 *
 * Headless this round: until a producer (P&L, historical balances) runs native, there are no
 * matching terminal activities, so this is a no-op — the wiring is what lands now.
 */
export const useSmartRerun = createSharedComposable((): UseSmartRerunReturn => {
  const autoRerunOnEdit = useSetting('autoRerunOnEdit');
  const { model } = useTaskCenter();
  const { rerun } = useTaskController();

  const needsRerun = ref<Activity[]>([]);

  function candidates(edit: EventMutated): Activity[] {
    const kinds = invalidatedKinds(edit.kind);
    if (kinds.length === 0)
      return [];

    return get(model).groups.flatMap(group => group.activities).filter(activity => activity.rerunnable && isTerminalStatus(activity.status) && kinds.includes(activity.kind));
  }

  function rerunAll(activities: Activity[]): void {
    for (const activity of activities)
      rerun(activity);
  }

  function onMutated(edit: EventMutated): void {
    const targets = candidates(edit);
    if (targets.length === 0)
      return;

    if (get(autoRerunOnEdit)) {
      rerunAll(targets);
      return;
    }

    // Surface for a later UI prompt; dedup by id so repeated edits don't pile the same work up.
    const byId = new Map(get(needsRerun).map(activity => [activity.id, activity]));
    for (const activity of targets)
      byId.set(activity.id, activity);
    set(needsRerun, Array.from(byId.values()));
  }

  function clear(): void {
    set(needsRerun, []);
  }

  function rerunPending(): void {
    rerunAll(get(needsRerun));
    clear();
  }

  taskCenterBus.on('event:mutated', onMutated);
  onScopeDispose(() => taskCenterBus.off('event:mutated', onMutated));

  return { clear, needsRerun, rerunPending };
});
