import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PendingTasks from '@/modules/core/notifications/PendingTasks.vue';
import { assembleActivityModel } from '@/modules/task-center/core/model';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
  type ActivityModel,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';

const activities = ref<Activity[]>([]);
const confirmCancel = vi.fn();

// The real model and the real job derivation run; only the orchestrator underneath is faked, so
// what the panel shows is what the tree actually produces.
vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { model: ComputedRef<ActivityModel> } => ({
    model: computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key)),
  }),
}));

vi.mock('@/modules/task-center/use-cancel-confirmation', () => ({
  useCancelConfirmation: (): { confirmCancel: (activity: Activity) => void } => ({ confirmCancel }),
}));

function activity(name: string, status: ActivityStatus, parent?: ActivityId): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TX_SYNC, name),
    kind: ActivityKind.TX_SYNC,
    parent,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    subtitle: name,
    title: 'Transaction sync',
  };
}

function umbrella(status: ActivityStatus): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.HISTORY_SYNC),
    kind: ActivityKind.HISTORY_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: 'History refresh',
  };
}

const umbrellaId = makeActivityId(ActivityKind.HISTORY_SYNC);

describe('pendingTasks', () => {
  beforeEach(() => {
    set(activities, []);
    confirmCancel.mockClear();
  });

  function createWrapper(): VueWrapper {
    return mount(PendingTasks, { props: { modelValue: true } });
  }

  it('should list the running activities when work is in flight', () => {
    set(activities, [activity('ethereum', ActivityStatus.RUNNING)]);

    expect(createWrapper().text()).toContain('collapsed_pending_tasks.title::1');
  });

  /**
   * The regression: `isActive` is WORKING while anything is RUNNING *or PENDING*, but this panel
   * lists live work only. Cancelling the last running activity while queued siblings remained left
   * the card rendered and spinning above the heading "0 pending tasks".
   */
  it('should not render the card when everything left is still queued', () => {
    set(activities, [activity('queued', ActivityStatus.PENDING)]);

    const text = createWrapper().text();
    expect(text).not.toContain('collapsed_pending_tasks.title');
    expect(text).toContain('no_task_running.description');
  });

  /**
   * The point of the whole change: one user action is one row with its work nested beneath it, not
   * four sibling rows that repeat the same title.
   */
  it('should show one job for a whole subtree, with its children under it', async () => {
    set(activities, [
      umbrella(ActivityStatus.RUNNING),
      activity('ethereum', ActivityStatus.RUNNING, umbrellaId),
      activity('gnosis', ActivityStatus.PENDING, umbrellaId),
    ]);

    const wrapper = createWrapper();

    // One row, not three siblings repeating the same title — the children are behind its disclosure.
    expect(wrapper.text()).toContain('collapsed_pending_tasks.title::1');
    expect(wrapper.text()).toContain('History refresh');
    expect(wrapper.text()).not.toContain('ethereum');

    await wrapper.find('[aria-expanded]').trigger('click');

    expect(wrapper.text()).toContain('ethereum');
    expect(wrapper.text()).toContain('gnosis');
  });

  it('should count steps in leaves, so intermediate rows do not inflate the total', () => {
    set(activities, [
      umbrella(ActivityStatus.RUNNING),
      activity('ethereum', ActivityStatus.COMPLETE, umbrellaId),
      activity('gnosis', ActivityStatus.RUNNING, umbrellaId),
    ]);

    expect(createWrapper().text()).toContain('collapsed_pending_tasks.steps::1, 2');
  });

  it('should hide the rows but keep the header when collapsed', () => {
    set(activities, [activity('ethereum', ActivityStatus.RUNNING)]);
    const wrapper = mount(PendingTasks, { props: { modelValue: false } });

    expect(wrapper.text()).toContain('collapsed_pending_tasks.title::1');
    expect(wrapper.text()).not.toContain('ethereum');
  });

  it('should ask for confirmation before cancelling a leaf', async () => {
    set(activities, [activity('ethereum', ActivityStatus.RUNNING)]);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=cancel-activity]').trigger('click');

    expect(confirmCancel).toHaveBeenCalledOnce();
  });
});
