import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PendingTasks from '@/modules/core/notifications/PendingTasks.vue';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';

const active = ref<Activity[]>([]);
const activities = ref<Activity[]>([]);
const isActive = ref<boolean>(false);

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { active: Ref<Activity[]>; isActive: Ref<boolean> } => ({ active, isActive }),
}));

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: (): { activities: Ref<Activity[]> } => ({ activities }),
}));

vi.mock('@/modules/task-center/use-task-controller', () => ({
  useTaskController: (): { cancel: () => Promise<void> } => ({ cancel: async (): Promise<void> => {} }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { dismiss: () => void; show: () => void } => ({ dismiss: (): void => {}, show: (): void => {} }),
}));

function activity(id: string, status: ActivityStatus): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, id),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: 'Blockchain balances',
  };
}

describe('pendingTasks', () => {
  beforeEach(() => {
    set(active, []);
    set(activities, []);
    set(isActive, false);
  });

  function createWrapper(): VueWrapper {
    return mount(PendingTasks, { props: { modelValue: true } });
  }

  it('should list the running activities when work is in flight', () => {
    set(active, [activity('a', ActivityStatus.RUNNING)]);
    set(isActive, true);

    expect(createWrapper().text()).toContain('collapsed_pending_tasks.title::1');
  });

  /**
   * The regression: `isActive` is WORKING while anything is RUNNING *or PENDING*, but this panel
   * lists RUNNING only. Cancelling the last running activity while queued siblings remained left
   * the card rendered and spinning above the heading "0 pending tasks".
   *
   * Producers declare their whole tree up front, so queued siblings are the normal case, not an
   * edge one — every account of every chain exists as a PENDING activity from the moment a refresh
   * starts.
   */
  it('should not render the card when everything left is still queued', () => {
    set(active, []);
    set(activities, [activity('queued', ActivityStatus.PENDING)]);
    set(isActive, true);

    const text = createWrapper().text();
    expect(text).not.toContain('collapsed_pending_tasks.title');
    expect(text).toContain('no_task_running.description');
  });
});
