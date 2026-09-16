import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
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
import { useDockPanel } from './use-dock-panel';
import { usePendingJobs } from './use-pending-jobs';

const activities = ref<Activity[]>([]);
const rerun = vi.fn<(activity: Activity) => void>();

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { isActive: ComputedRef<boolean>; model: ComputedRef<ActivityModel> } => {
    const model = computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key));
    return { isActive: computed<boolean>(() => get(model).overall.phase === ActivityPhase.WORKING), model };
  },
}));

vi.mock('@/modules/task-center/use-task-controller', () => ({
  useTaskController: (): { rerun: typeof rerun } => ({ rerun }),
}));

function activity(kind: ActivityKind, name: string, status: ActivityStatus, parent?: ActivityId, partial: Partial<Activity> = {}): Activity {
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
    ...partial,
  };
}

const balancesId = makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'run');

/** A balance refresh over three chains, with the given statuses, one of which can be run again. */
function balances(run: ActivityStatus, eth: ActivityStatus, gnosis: ActivityStatus, sonic: ActivityStatus): Activity[] {
  return [
    activity(ActivityKind.BLOCKCHAIN_BALANCES, 'run', run),
    activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', eth, balancesId),
    activity(ActivityKind.BLOCKCHAIN_BALANCES, 'gnosis', gnosis, balancesId, { rerunnable: true }),
    activity(ActivityKind.BLOCKCHAIN_BALANCES, 'sonic', sonic, balancesId),
  ];
}

function report(status: ActivityStatus): Activity {
  return activity(ActivityKind.PNL_REPORT, 'report', status);
}

let scope: ReturnType<typeof effectScope> | undefined;

function panel(): ReturnType<typeof useDockPanel> {
  scope = effectScope();
  return scope.run(() => {
    const { children, jobs } = usePendingJobs();
    return useDockPanel(jobs, children);
  })!;
}

async function transition(next: Activity[]): Promise<void> {
  set(activities, next);
  await nextTick();
}

const { COMPLETE, FAILED, RUNNING } = ActivityStatus;

describe('useDockPanel', () => {
  beforeEach(() => {
    set(activities, []);
    rerun.mockClear();
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
  });

  describe('while working', () => {
    it('should list the jobs in flight, and count their leaves', () => {
      set(activities, [...balances(RUNNING, COMPLETE, RUNNING, FAILED), report(RUNNING)]);
      const { roots, summary, tally, title, total } = panel();

      expect(get(roots).map(root => root.kind)).toEqual([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.PNL_REPORT]);
      expect(get(total)).toBe(4);
      expect(get(tally)[COMPLETE]).toBe(1);
      expect(get(tally)[RUNNING]).toBe(2);
      expect(get(title)).toBe('task_dock.panel.title.working');
      expect(get(summary)).toBe(true);
    });

    it('should not summarise a single job, whose own row shows its progress', () => {
      set(activities, balances(RUNNING, COMPLETE, RUNNING, RUNNING));

      expect(get(panel().summary)).toBe(false);
    });

    it('should list a running job that already has a failed leaf ahead of one listed before it', () => {
      const history = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');
      set(activities, [
        ...balances(RUNNING, COMPLETE, RUNNING, RUNNING),
        activity(ActivityKind.HISTORY_SYNC, 'refresh', RUNNING),
        activity(ActivityKind.TX_SYNC, 'eth', FAILED, history),
        activity(ActivityKind.TX_SYNC, 'gnosis', RUNNING, history),
      ]);

      expect(get(panel().roots).map(root => root.kind)).toEqual([ActivityKind.HISTORY_SYNC, ActivityKind.BLOCKCHAIN_BALANCES]);
    });

    it('should offer nothing to retry while work still runs, even with a leaf already failed', () => {
      set(activities, balances(RUNNING, COMPLETE, FAILED, RUNNING));

      expect(get(panel().retryable)).toEqual([]);
    });
  });

  describe('once the run settles', () => {
    it('should say the run finished with problems, counting failed leaves across every job', async () => {
      set(activities, [report(RUNNING), ...balances(RUNNING, RUNNING, RUNNING, RUNNING)]);
      const { tally, title } = panel();

      await transition([report(FAILED), ...balances(COMPLETE, COMPLETE, FAILED, COMPLETE)]);

      expect(get(title)).toBe('task_dock.panel.title.problems');
      expect(get(tally)[FAILED]).toBe(2);
    });

    it('should offer to retry only the failed leaves that can run again, and rerun each of them', async () => {
      set(activities, balances(RUNNING, RUNNING, RUNNING, RUNNING));
      const { retryable, retryFailed } = panel();

      await transition(balances(COMPLETE, COMPLETE, FAILED, FAILED));

      expect(get(retryable).map(leaf => leaf.id)).toEqual([makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'gnosis')]);

      retryFailed();

      expect(rerun).toHaveBeenCalledOnce();
      expect(rerun.mock.calls[0]?.[0]).toMatchObject({ id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'gnosis') });
    });

    it('should say a clean run finished, with nothing to retry', async () => {
      set(activities, balances(RUNNING, RUNNING, RUNNING, RUNNING));
      const { retryable, title } = panel();

      await transition(balances(COMPLETE, COMPLETE, COMPLETE, COMPLETE));

      expect(get(title)).toBe('task_dock.panel.title.finished');
      expect(get(retryable)).toEqual([]);
    });
  });

  describe('sections', () => {
    it('should give no heading to a kind listed once, since its job already names it', () => {
      set(activities, [...balances(RUNNING, RUNNING, RUNNING, RUNNING), report(RUNNING)]);

      expect(get(panel().sections).map(section => section.title)).toEqual([undefined, undefined]);
    });

    it('should head a kind listed more than once, grouping its jobs together', () => {
      set(activities, [
        activity(ActivityKind.EXCHANGE_BALANCES, 'kraken', RUNNING),
        report(RUNNING),
        activity(ActivityKind.EXCHANGE_BALANCES, 'binance', RUNNING),
      ]);

      const sections = get(panel().sections);

      expect(sections.map(section => section.roots.length)).toEqual([2, 1]);
      expect(sections[0]?.title).toBeDefined();
      expect(sections[1]?.title).toBeUndefined();
    });
  });
});
