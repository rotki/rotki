import { ok } from 'plainfp/result';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { EditKind } from './core/rerun/policy';
import {
  type Activity,
  ActivityKind,
  type ActivityModel,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from './core/types';
import { taskCenterBus } from './events/task-center-bus';
import { useSmartRerun } from './use-smart-rerun';

const rerun = vi.fn(() => ok(undefined));
const modelRef = ref<ActivityModel>(model([]));

vi.mock('./use-task-controller', () => ({ useTaskController: (): { rerun: typeof rerun } => ({ rerun }) }));
vi.mock('./use-task-center', () => ({ useTaskCenter: (): { model: typeof modelRef } => ({ model: modelRef }) }));

function activity(kind: ActivityKind, status: ActivityStatus, rerunnable: boolean, part = 'x'): Activity {
  return {
    cancellable: false,
    id: makeActivityId(kind, part),
    kind,
    percentage: 100,
    rerunnable,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: 't',
  };
}

function model(activities: Activity[]): ActivityModel {
  return {
    active: [],
    groups: [{ activities, kind: ActivityKind.OTHER, percentage: -1, status: ActivityStatus.COMPLETE, title: 'g' }],
    overall: { percentage: 100, phase: 'done' },
    pending: [],
  };
}

describe('useSmartRerun', () => {
  let smart: ReturnType<typeof useSmartRerun>;

  beforeAll(() => {
    setActivePinia(createPinia());
    smart = useSmartRerun();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    useSettingsRepo().updateFrontend({ autoRerunOnEdit: false });
    modelRef.value = model([]);
    smart.clear();
  });

  it('should re-run invalidated terminal activities immediately when autoRerunOnEdit is on', () => {
    const hist = activity(ActivityKind.HISTORICAL_BALANCES, ActivityStatus.COMPLETE, true);
    modelRef.value = model([hist]);
    useSettingsRepo().updateFrontend({ autoRerunOnEdit: true });

    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_DELETED });

    expect(rerun).toHaveBeenCalledWith(hist);
    expect(smart.needsRerun.value).toEqual([]);
  });

  it('should collect invalidated activities into needsRerun when autoRerunOnEdit is off', () => {
    const hist = activity(ActivityKind.HISTORICAL_BALANCES, ActivityStatus.COMPLETE, true);
    modelRef.value = model([hist]);

    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_REDECODED });

    expect(rerun).not.toHaveBeenCalled();
    expect(smart.needsRerun.value).toEqual([hist]);
  });

  it('should ignore running, non-rerunnable, or unaffected activities', () => {
    const running = activity(ActivityKind.HISTORICAL_BALANCES, ActivityStatus.RUNNING, true, 'a');
    const notRerunnable = activity(ActivityKind.HISTORICAL_BALANCES, ActivityStatus.COMPLETE, false, 'b');
    // PNL_REPORT is intentionally excluded from the policy, so a terminal rerunnable one is unaffected.
    const unaffected = activity(ActivityKind.PNL_REPORT, ActivityStatus.COMPLETE, true);
    modelRef.value = model([running, notRerunnable, unaffected]);

    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_DELETED });

    expect(smart.needsRerun.value).toEqual([]);
  });

  it('should dedupe repeated edits by activity id', () => {
    const hist = activity(ActivityKind.HISTORICAL_BALANCES, ActivityStatus.COMPLETE, true);
    modelRef.value = model([hist]);

    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_DELETED });
    taskCenterBus.emit('event:mutated', { kind: EditKind.TRANSACTION_DELETED });

    expect(smart.needsRerun.value).toEqual([hist]);
  });

  it('should re-run and clear pending activities on rerunPending', () => {
    const hist = activity(ActivityKind.HISTORICAL_BALANCES, ActivityStatus.COMPLETE, true);
    modelRef.value = model([hist]);
    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_DELETED });

    smart.rerunPending();

    expect(rerun).toHaveBeenCalledWith(hist);
    expect(smart.needsRerun.value).toEqual([]);
  });
});
