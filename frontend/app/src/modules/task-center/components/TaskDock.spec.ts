import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TaskDock from '@/modules/task-center/components/TaskDock.vue';
import { assembleActivityModel } from '@/modules/task-center/core/model';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
  type ActivityModel,
  ActivityPhase,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';

const activities = ref<Activity[]>([]);
const confirmCancel = vi.fn();

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { isActive: ComputedRef<boolean>; model: ComputedRef<ActivityModel> } => {
    const model = computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key));
    return { isActive: computed<boolean>(() => get(model).overall.phase === ActivityPhase.WORKING), model };
  },
}));

vi.mock('@/modules/task-center/use-cancel-confirmation', () => ({
  useCancelConfirmation: (): { confirmCancel: (activity: Activity) => void } => ({ confirmCancel }),
}));

function activity(kind: ActivityKind, name: string, status: ActivityStatus, parent?: ActivityId): Activity {
  return {
    cancellable: true,
    id: makeActivityId(kind, name),
    kind,
    parent,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    subtitle: name,
    title: `${kind} title`,
  };
}

const refreshId = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');

function createWrapper(): VueWrapper {
  return mount(TaskDock);
}

describe('taskDock', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(activities, []);
    confirmCancel.mockClear();
  });

  it('should render nothing while no work is running or queued', () => {
    expect(createWrapper().find('[data-testid=task-dock-pill]').exists()).toBe(false);
  });

  it('should name the long job on the pill, with its leaf count and the other jobs counted', () => {
    set(activities, [
      activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING),
      activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING),
      activity(ActivityKind.TX_SYNC, 'eth', ActivityStatus.COMPLETE, refreshId),
      activity(ActivityKind.TX_SYNC, 'gnosis', ActivityStatus.RUNNING, refreshId),
    ]);

    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('history-sync title');
    expect(wrapper.find('[data-testid=task-dock-steps]').text()).toBe('pending_task.steps::1, 2');
    expect(wrapper.find('[data-testid=task-dock-more]').text()).toBe('task_dock.more::1');
  });

  it('should count a single long activity on the pill by its own steps', () => {
    set(activities, [{ ...activity(ActivityKind.PRICES, 'latest', ActivityStatus.RUNNING), percentage: 33, steps: { current: 1, total: 3 } }]);

    expect(createWrapper().find('[data-testid=task-dock-steps]').text()).toBe('pending_task.steps::1, 3');
  });

  /**
   * `isActive` is WORKING while anything is RUNNING *or PENDING*, but the panel lists running work
   * only. The removed sidebar list once rendered "0 pending tasks" above an empty body in exactly this
   * state, so queued-only work keeps the pill and opens nothing.
   */
  it('should say the work is queued, and open no empty panel, while nothing has started', async () => {
    set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.PENDING)]);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('task_dock.queued');

    await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

    expect(wrapper.find('[data-testid=task-dock-panel]').exists()).toBe(false);
  });

  it('should open the job tree from the pill and close it from the panel header', async () => {
    set(activities, [
      activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING),
      activity(ActivityKind.TX_SYNC, 'ethereum', ActivityStatus.RUNNING, refreshId),
    ]);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=task-dock-pill]').trigger('click');
    const panel = wrapper.find('[data-testid=task-dock-panel]');
    expect(panel.text()).toContain('history-sync title');
    expect(panel.text()).not.toContain('ethereum');

    await panel.find('[aria-expanded]').trigger('click');
    expect(wrapper.find('[data-testid=task-dock-panel]').text()).toContain('ethereum');

    await wrapper.find('[aria-label="pending_task.collapse"]').trigger('click');
    expect(wrapper.find('[data-testid=task-dock-panel]').exists()).toBe(false);
  });

  it('should ask for confirmation before cancelling a row', async () => {
    set(activities, [activity(ActivityKind.TX_SYNC, 'ethereum', ActivityStatus.RUNNING)]);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=task-dock-pill]').trigger('click');
    await wrapper.find('[data-testid=cancel-activity]').trigger('click');

    expect(confirmCancel).toHaveBeenCalledOnce();
  });
});
