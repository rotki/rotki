import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
const confirmCancel = vi.fn<(activity: Activity) => void>();
const confirmCancelAll = vi.fn<(targets: Activity[], keptRunning: number) => void>();
const rerun = vi.fn<(activity: Activity) => void>();

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { isActive: ComputedRef<boolean>; model: ComputedRef<ActivityModel> } => {
    const model = computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key));
    return { isActive: computed<boolean>(() => get(model).overall.phase === ActivityPhase.WORKING), model };
  },
}));

vi.mock('@/modules/task-center/use-cancel-confirmation', () => ({
  useCancelConfirmation: (): { confirmCancel: typeof confirmCancel; confirmCancelAll: typeof confirmCancelAll } => ({ confirmCancel, confirmCancelAll }),
}));

vi.mock('@/modules/task-center/use-task-controller', () => ({
  useTaskController: (): { rerun: typeof rerun } => ({ rerun }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => ref<boolean>(false),
}));

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: (): { loading: Ref<boolean>; useApiKey: () => Ref<string> } => ({ loading: ref(false), useApiKey: () => ref('') }),
}));

function activity(kind: ActivityKind, name: string, status: ActivityStatus, parent?: ActivityId, rerunnable = false): Activity {
  return {
    cancellable: true,
    id: makeActivityId(kind, name),
    kind,
    parent,
    percentage: -1,
    rerunnable,
    source: { type: ActivitySourceType.NATIVE },
    status,
    subtitle: name,
    title: `${kind} title`,
  };
}

const refreshId = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');

function refresh(status: ActivityStatus, chain: ActivityStatus = status): Activity[] {
  return [
    activity(ActivityKind.HISTORY_SYNC, 'refresh', status),
    activity(ActivityKind.TX_SYNC, 'ethereum', chain, refreshId),
  ];
}

function createWrapper(): VueWrapper {
  return mount(TaskDock);
}

describe('taskDock', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(activities, []);
    vi.clearAllMocks();
  });

  it('should explain a history sync under its own job while it runs, and say nothing of it for other work', async () => {
    set(activities, [...refresh(ActivityStatus.RUNNING), activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING)]);
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

    const hints = wrapper.findAll('[data-testid=dock-sync-hint]');
    expect(hints).toHaveLength(1);
    expect(wrapper.find('[data-testid=dock-panel-header] ~ [data-testid=dock-sync-hint]').exists()).toBe(false);

    set(activities, [activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING)]);
    await nextTick();

    expect(wrapper.find('[data-testid=dock-sync-hint]').exists()).toBe(false);
  });

  describe('the panel footer', () => {
    it('should offer to stop the jobs it may safely interrupt, naming how many data-changing jobs keep running', async () => {
      set(activities, [
        ...refresh(ActivityStatus.RUNNING),
        activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING),
        activity(ActivityKind.ASSETS, 'update', ActivityStatus.RUNNING),
      ]);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');
      expect(wrapper.find('[data-testid=dock-retry-failed]').exists()).toBe(false);

      await wrapper.find('[data-testid=dock-stop-all]').trigger('click');

      expect(confirmCancelAll).toHaveBeenCalledOnce();
      const [targets, keptRunning] = confirmCancelAll.mock.calls[0] ?? [];
      expect(targets?.map(target => target.kind).sort()).toEqual([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.HISTORY_SYNC]);
      expect(keptRunning).toBe(1);
    });

    it('should not offer stop all when only one of the running jobs is safe to interrupt', async () => {
      set(activities, [...refresh(ActivityStatus.RUNNING), activity(ActivityKind.CSV_IMPORT, 'import', ActivityStatus.RUNNING)]);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

      expect(wrapper.find('[data-testid=dock-stop-all]').exists()).toBe(false);
    });

    it('should leave stopping a single job to its own row', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

      expect(wrapper.find('[data-testid=dock-stop-all]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=cancel-activity]').exists()).toBe(true);
    });

    it('should offer to retry every failed leaf once the run settles with several, instead of stopping', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();
      const settledRun = [
        activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE),
        { ...activity(ActivityKind.TX_SYNC, 'ethereum', ActivityStatus.FAILED, refreshId, true), reason: 'rate limited' },
        { ...activity(ActivityKind.TX_SYNC, 'gnosis', ActivityStatus.FAILED, refreshId, true), reason: 'no API key' },
      ];

      set(activities, settledRun);
      await nextTick();
      await nextTick();
      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

      expect(wrapper.find('[data-testid=dock-stop-all]').exists()).toBe(false);
      const retry = wrapper.find('[data-testid=dock-retry-failed]');
      expect(retry.text()).toBe('task_dock.panel.retry_failed::2');

      await retry.trigger('click');

      expect(rerun).toHaveBeenCalledTimes(2);
    });

    it('should leave retrying failures that share a reason under one job to their group', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      set(activities, [
        activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE),
        { ...activity(ActivityKind.TX_SYNC, 'ethereum', ActivityStatus.FAILED, refreshId, true), reason: 'no API key' },
        { ...activity(ActivityKind.TX_SYNC, 'gnosis', ActivityStatus.FAILED, refreshId, true), reason: 'no API key' },
      ]);
      await nextTick();
      await nextTick();
      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

      expect(wrapper.find('[data-testid=dock-failed-group-retry]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=dock-retry-failed]').exists()).toBe(false);
    });

    it('should leave retrying a single failure to its own row', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      set(activities, [
        activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE),
        activity(ActivityKind.TX_SYNC, 'ethereum', ActivityStatus.FAILED, refreshId, true),
      ]);
      await nextTick();
      await nextTick();
      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');

      expect(wrapper.find('[data-testid=dock-retry-failed]').exists()).toBe(false);
    });

    it('should rerun a failed leaf from its own row', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      set(activities, [
        activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE),
        activity(ActivityKind.TX_SYNC, 'ethereum', ActivityStatus.FAILED, refreshId, true),
      ]);
      await nextTick();
      await nextTick();
      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');
      await wrapper.find('[data-testid=retry-activity]').trigger('click');

      expect(rerun).toHaveBeenCalledOnce();
    });
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

    expect(wrapper.find('[data-testid=task-dock-pill]').attributes('data-state')).toBe('working');
    expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('history-sync title');
    expect(wrapper.find('[data-testid=task-dock-steps]').text()).toBe('pending_task.steps::1, 2');
    expect(wrapper.find('[data-testid=task-dock-more]').text()).toBe('task_dock.more::1');
  });

  it('should count a single ranked activity on the pill by its own steps', () => {
    set(activities, [{ ...activity(ActivityKind.HISTORICAL_BALANCES, 'range', ActivityStatus.RUNNING), percentage: 33, steps: { current: 1, total: 3 } }]);

    expect(createWrapper().find('[data-testid=task-dock-steps]').text()).toBe('pending_task.steps::1, 3');
  });

  it('should name the balance refresh over a price refresh, as the login load runs them', () => {
    set(activities, [
      activity(ActivityKind.PRICES, 'latest', ActivityStatus.RUNNING),
      activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING),
    ]);

    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('blockchain-balances title');
    expect(wrapper.find('[data-testid=task-dock-more]').text()).toBe('task_dock.more::1');
  });

  it('should describe upkeep generically, without a count, while nothing ranked runs', () => {
    set(activities, [{ ...activity(ActivityKind.PRICES, 'latest', ActivityStatus.RUNNING), percentage: 33, steps: { current: 1, total: 3 } }]);

    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('task_dock.updating');
    expect(wrapper.find('[data-testid=task-dock-steps]').exists()).toBe(false);
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

  describe('once the run settles', () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    async function settle(wrapper: VueWrapper, next: Activity[]): Promise<void> {
      set(activities, next);
      await nextTick();
      await nextTick();
      await wrapper.vm.$nextTick();
    }

    it('should shrink a dismissed failure to an icon that reopens it, with nothing left to dismiss', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      await settle(wrapper, refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');
      await wrapper.find('[data-testid=dismiss-activity]').trigger('click');

      const pill = wrapper.find('[data-testid=task-dock-pill]');
      expect(pill.attributes('data-state')).toBe('dismissed');
      expect(wrapper.find('[data-testid=task-dock-caption]').classes()).toContain('sr-only');
      expect(wrapper.find('[data-testid=task-dock-panel]').exists()).toBe(false);

      await pill.trigger('click');
      const panel = wrapper.find('[data-testid=task-dock-panel]');
      expect(panel.text()).toContain('history-sync title');
      expect(panel.find('[data-testid=dismiss-activity]').exists()).toBe(false);
    });

    it('should list a failed job in the panel until its own row is dismissed', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      await settle(wrapper, refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));

      const pill = wrapper.find('[data-testid=task-dock-pill]');
      expect(pill.attributes('data-state')).toBe('failed');

      await pill.trigger('click');
      const panel = wrapper.find('[data-testid=task-dock-panel]');
      expect(panel.text()).toContain('history-sync title');
      expect(panel.findAll('[data-testid=dismiss-activity]')).toHaveLength(1);

      await wrapper.find('[aria-label="pending_task.collapse"]').trigger('click');
      expect(wrapper.find('[data-testid=task-dock-pill]').attributes('data-state')).toBe('failed');

      await wrapper.find('[data-testid=task-dock-pill]').trigger('click');
      await wrapper.find('[data-testid=dismiss-activity]').trigger('click');
      expect(wrapper.find('[data-testid=task-dock-pill]').attributes('data-state')).toBe('dismissed');
    });

    it('should name the one failed leaf rather than blame the whole job', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      await settle(wrapper, refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));

      expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('task_dock.failed_leaf::ethereum');
    });

    it('should count failed leaves against every leaf of the job when several failed', async () => {
      const runId = makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'run');
      const balances = (run: ActivityStatus, eth: ActivityStatus, sonic: ActivityStatus, gnosis: ActivityStatus): Activity[] => [
        activity(ActivityKind.BLOCKCHAIN_BALANCES, 'run', run),
        activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', eth, runId),
        activity(ActivityKind.BLOCKCHAIN_BALANCES, 'sonic', sonic, runId),
        activity(ActivityKind.BLOCKCHAIN_BALANCES, 'gnosis', gnosis, runId),
      ];
      const { COMPLETE, FAILED, RUNNING } = ActivityStatus;
      set(activities, balances(RUNNING, RUNNING, RUNNING, RUNNING));
      const wrapper = createWrapper();

      await settle(wrapper, balances(COMPLETE, COMPLETE, FAILED, FAILED));

      expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('task_dock.failed_leaves::2, blockchain-balances title, 3');
    });

    it('should name the job when the failure sits on the job itself, not on a leaf', async () => {
      set(activities, [activity(ActivityKind.PNL_REPORT, 'report', ActivityStatus.RUNNING)]);
      const wrapper = createWrapper();

      await settle(wrapper, [activity(ActivityKind.PNL_REPORT, 'report', ActivityStatus.FAILED)]);

      expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('task_dock.failed::pnl-report title');
    });

    it('should keep naming a finished job on the pill until its row is dismissed, then shrink to a check', async () => {
      vi.useFakeTimers();
      set(activities, refresh(ActivityStatus.RUNNING));
      const wrapper = createWrapper();

      set(activities, refresh(ActivityStatus.COMPLETE));
      await nextTick();
      await nextTick();
      await vi.advanceTimersByTimeAsync(60000);

      const pill = wrapper.find('[data-testid=task-dock-pill]');
      expect(pill.attributes('data-state')).toBe('done');
      expect(wrapper.find('[data-testid=task-dock-caption]').text()).toBe('task_dock.done::history-sync title');

      await pill.trigger('click');
      await wrapper.find('[data-testid=dismiss-activity]').trigger('click');

      expect(wrapper.find('[data-testid=task-dock-pill]').attributes('data-state')).toBe('dismissed');
      expect(wrapper.find('[data-testid=task-dock-caption]').classes()).toContain('sr-only');
    });
  });
});
