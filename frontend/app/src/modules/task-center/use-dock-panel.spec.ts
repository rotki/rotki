import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { type ActivityModel, assembleActivityModel } from '@/modules/task-center/core/model';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
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

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => ref<boolean>(false),
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

const { COMPLETE, FAILED, RUNNING, SKIPPED } = ActivityStatus;

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

    it('should list jobs in the order they started, not by kind, and not move one that fails', () => {
      const history = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');
      const long = Date.now() - 60_000;
      set(activities, [
        activity(ActivityKind.HISTORY_SYNC, 'refresh', RUNNING, undefined, { startedAt: long + 1000 }),
        activity(ActivityKind.TX_SYNC, 'eth', FAILED, history),
        activity(ActivityKind.TX_SYNC, 'gnosis', RUNNING, history),
        report(RUNNING),
        ...balances(RUNNING, COMPLETE, RUNNING, RUNNING).map(item => ({ ...item, startedAt: long })),
      ].map(item => (item.kind === ActivityKind.PNL_REPORT ? { ...item, startedAt: long + 2000 } : item)));

      expect(get(panel().roots).map(root => root.kind)).toEqual([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.HISTORY_SYNC, ActivityKind.PNL_REPORT]);
    });

    it('should keep a job that finishes mid-run where it was until the run ends', async () => {
      const long = Date.now() - 60_000;
      const pnl = (status: ActivityStatus): Activity => ({ ...report(status), startedAt: long });
      const later = balances(RUNNING, RUNNING, RUNNING, RUNNING).map(item => ({ ...item, startedAt: long + 1000 }));
      set(activities, [pnl(RUNNING), ...later]);
      const { roots } = panel();
      await nextTick();

      await transition([pnl(COMPLETE), ...later]);

      expect(get(roots).map(root => root.kind)).toEqual([ActivityKind.PNL_REPORT, ActivityKind.BLOCKCHAIN_BALANCES]);
    });

    it('should not list a job until it has run for a moment, unless it fails', async () => {
      const long = Date.now() - 60_000;
      const history = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');
      set(activities, [
        ...balances(RUNNING, RUNNING, RUNNING, RUNNING).map(item => ({ ...item, startedAt: long })),
        activity(ActivityKind.PRICES, 'latest', RUNNING, undefined, { startedAt: Date.now() }),
        activity(ActivityKind.HISTORY_SYNC, 'refresh', RUNNING, undefined, { startedAt: Date.now() }),
        activity(ActivityKind.TX_SYNC, 'eth', FAILED, history),
        activity(ActivityKind.TX_SYNC, 'gnosis', RUNNING, history),
      ]);

      expect(get(panel().roots).map(root => root.kind)).toEqual([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.HISTORY_SYNC]);
    });

    it('should split running jobs into the ones a bulk stop may interrupt and the ones it leaves running', () => {
      set(activities, [
        ...balances(RUNNING, RUNNING, RUNNING, RUNNING),
        activity(ActivityKind.CSV_IMPORT, 'import', RUNNING),
        activity(ActivityKind.HISTORY_SYNC, 'refresh', RUNNING),
      ]);
      const { stoppable, unstoppable } = panel();

      expect(get(stoppable).map(root => root.kind).sort()).toEqual([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.HISTORY_SYNC]);
      expect(get(unstoppable).map(root => root.kind)).toEqual([ActivityKind.CSV_IMPORT]);
    });

    it('should leave running a job of a safe kind whose subtree deletes before re-deriving', () => {
      const refreshId = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');
      set(activities, [
        activity(ActivityKind.HISTORY_SYNC, 'refresh', RUNNING),
        activity(ActivityKind.TX_DECODING, 'redecode', RUNNING, refreshId, { resets: true }),
      ]);
      const { stoppable, unstoppable } = panel();

      expect(get(stoppable)).toEqual([]);
      expect(get(unstoppable).map(root => root.id)).toEqual([refreshId]);
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

    it('should list a job the user started above the upkeep that started before it', async () => {
      const imported = (status: ActivityStatus): Activity =>
        activity(ActivityKind.ACCOUNTS, 'import', status, undefined, { startedAt: 2, userStarted: true });
      const background = (status: ActivityStatus): Activity[] =>
        balances(status, status, status, status).map(item => (item.parent ? item : { ...item, startedAt: 1 }));
      set(activities, [...background(RUNNING), imported(RUNNING)]);
      const { roots } = panel();

      expect(get(roots).map(root => root.kind)).toEqual([ActivityKind.BLOCKCHAIN_BALANCES, ActivityKind.ACCOUNTS]);

      await transition([...background(COMPLETE), imported(COMPLETE)]);

      expect(get(roots).map(root => root.kind)).toEqual([ActivityKind.ACCOUNTS, ActivityKind.BLOCKCHAIN_BALANCES]);
    });

    it('should say the run needs attention, listing only the job whose skip asked for it', async () => {
      set(activities, [report(RUNNING), ...balances(RUNNING, RUNNING, RUNNING, RUNNING)]);
      const { roots, title } = panel();

      const skipped = balances(COMPLETE, COMPLETE, SKIPPED, COMPLETE)
        .map(item => (item.status === SKIPPED ? { ...item, attention: true } : item));
      await transition([report(COMPLETE), ...skipped]);

      expect(get(title)).toBe('task_dock.panel.title.attention');
      expect(get(roots).map(root => root.id)).toEqual([balancesId]);
    });
  });

  describe('sections', () => {
    it('should give no heading to a kind listed once, since its job already names it', () => {
      set(activities, [...balances(RUNNING, RUNNING, RUNNING, RUNNING), report(RUNNING)]);

      expect(get(panel().sections).map(section => section.title)).toEqual([undefined, undefined]);
    });

    it('should keep every job its own untitled section while work runs, so none moves to join its kind', () => {
      set(activities, [
        activity(ActivityKind.EXCHANGE_BALANCES, 'kraken', RUNNING),
        report(RUNNING),
        activity(ActivityKind.EXCHANGE_BALANCES, 'binance', RUNNING),
      ]);

      const sections = get(panel().sections);

      expect(sections.map(section => section.roots.length)).toEqual([1, 1, 1]);
      expect(sections.map(section => section.title)).toEqual([undefined, undefined, undefined]);
    });

    it('should head a kind reported more than once, grouping its jobs together, once the run settles', async () => {
      const jobs = (status: ActivityStatus): Activity[] => [
        activity(ActivityKind.EXCHANGE_BALANCES, 'kraken', status),
        report(status),
        activity(ActivityKind.EXCHANGE_BALANCES, 'binance', status),
      ];
      set(activities, jobs(RUNNING));
      const { sections } = panel();
      await nextTick();

      await transition(jobs(COMPLETE));

      expect(get(sections).map(section => section.roots.length)).toEqual([2, 1]);
      expect(get(sections)[0]?.title).toBeDefined();
      expect(get(sections)[1]?.title).toBeUndefined();
    });
  });
});
