import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { msg } from '@/message-key';
import { type ActivityModel, assembleActivityModel } from './core/model';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  type ActivityWaiting,
  makeActivityId,
  WaitingReason,
} from './core/types';
import { useWaitingLabel } from './use-waiting-label';

const activities = ref<Activity[]>([]);

vi.mock('./use-task-center', () => ({
  useTaskCenter: (): { model: ComputedRef<ActivityModel> } => ({
    model: computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key)),
  }),
}));

const ethereum: Activity = {
  cancellable: false,
  id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'),
  kind: ActivityKind.BLOCKCHAIN_BALANCES,
  percentage: -1,
  rerunnable: false,
  source: { type: ActivitySourceType.NATIVE },
  status: ActivityStatus.RUNNING,
  subtitle: { key: msg.$t('task_center.activity.blockchain_balances.chain'), params: { chain: 'Ethereum' } },
  title: 'Blockchain balances',
};

function queued(waiting?: ActivityWaiting): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.PNL_REPORT, 'report'),
    kind: ActivityKind.PNL_REPORT,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.PENDING,
    title: 'Profit and loss report',
    waiting,
  };
}

describe('useWaitingLabel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(activities, [ethereum]);
  });

  it('should say nothing for an activity that is not waiting', () => {
    expect(useWaitingLabel().waitingLabel(queued())).toBeUndefined();
  });

  it('should name the dependency by what it acts on', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: ethereum.id, reason: WaitingReason.DEPENDENCY }));

    expect(label).toBe('task_dock.waiting.dependency::Ethereum');
  });

  it('should name the parent a child waits to start', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: ethereum.id, reason: WaitingReason.PARENT }));

    expect(label).toBe('task_dock.waiting.parent::Ethereum');
  });

  it('should fall back to other work when what it waits on has left the model', () => {
    const label = useWaitingLabel().waitingLabel(queued({ on: makeActivityId(ActivityKind.TX_SYNC, 'gone'), reason: WaitingReason.DEPENDENCY }));

    expect(label).toBe('task_dock.waiting.other_work');
  });

  it.each([
    [WaitingReason.HISTORY_SYNC, 'task_dock.waiting.history_sync'],
    [WaitingReason.REDECODE, 'task_dock.waiting.redecode'],
    [WaitingReason.MATCHING, 'task_dock.waiting.matching'],
    [WaitingReason.SLOT, 'task_dock.waiting.slot'],
  ])('should explain a %s hold in its own words', (reason, key) => {
    expect(useWaitingLabel().waitingLabel(queued({ reason }))).toBe(key);
  });
});
