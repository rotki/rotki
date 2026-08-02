import { err, isErr, isOk, ok, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { type ControlError, NotCancellable, NotRerunnable } from './core/orchestrator/errors';
import { type Activity, ActivityKind, type ActivityModel, ActivitySourceType, ActivityStatus, makeActivityId, makeGroupId } from './core/types';
import { useTaskController } from './use-task-controller';

const orchestrator = {
  cancel: vi.fn((): Result<void, ControlError> => ok(undefined)),
  rerun: vi.fn((): Result<void, ControlError> => ok(undefined)),
};
const modelRef = ref<ActivityModel>(emptyModel());

vi.mock('./use-task-orchestrator', () => ({ useTaskOrchestrator: (): typeof orchestrator => orchestrator }));
vi.mock('./use-task-center', () => ({ useTaskCenter: (): { model: typeof modelRef } => ({ model: modelRef }) }));

function activity(overrides: Partial<Activity> & Pick<Activity, 'source'>): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.OTHER, 'x'),
    kind: ActivityKind.OTHER,
    percentage: -1,
    rerunnable: false,
    status: ActivityStatus.RUNNING,
    title: 'x',
    ...overrides,
  };
}

function emptyModel(activities: Activity[] = []): ActivityModel {
  return {
    active: activities,
    current: activities[0],
    groups: [{ activities, kind: ActivityKind.OTHER, percentage: -1, status: ActivityStatus.RUNNING, title: 'g' }],
    overall: { percentage: 0, phase: 'working' },
    pending: [],
  };
}

describe('useTaskController', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modelRef.value = emptyModel();
  });

  it('should route a native cancel to the orchestrator', async () => {
    const id = makeActivityId(ActivityKind.PRICES, 'p');
    const result = await useTaskController().cancel(activity({ id, source: { type: ActivitySourceType.NATIVE } }));
    expect(orchestrator.cancel).toHaveBeenCalledWith(id);
    expect(isOk(result)).toBe(true);
  });

  it('should surface the orchestrator NotCancellable rejection for a native activity', async () => {
    const id = makeActivityId(ActivityKind.PRICES, 'p');
    orchestrator.cancel.mockReturnValueOnce(err(NotCancellable({ id })));
    const result = await useTaskController().cancel(activity({ cancellable: false, id, source: { type: ActivitySourceType.NATIVE } }));
    assert(isErr(result));
    expect(hasTag(result.error, 'NotCancellable')).toBe(true);
  });

  it('should route a rerun to the orchestrator', () => {
    const id = makeActivityId(ActivityKind.PRICES, 'p');
    const result = useTaskController().rerun(activity({ id, source: { type: ActivitySourceType.NATIVE } }));
    expect(orchestrator.rerun).toHaveBeenCalledWith(id);
    expect(isOk(result)).toBe(true);
  });

  it('should surface the orchestrator NotRerunnable rejection', () => {
    const id = makeActivityId(ActivityKind.PRICES, 'p');
    orchestrator.rerun.mockReturnValueOnce(err(NotRerunnable({ id })));
    const result = useTaskController().rerun(activity({ id, source: { type: ActivitySourceType.NATIVE } }));
    assert(isErr(result));
    expect(hasTag(result.error, 'NotRerunnable')).toBe(true);
  });

  it('should cancel only the activities in a group', async () => {
    const group = makeGroupId('batch');
    const inGroup = activity({
      group,
      id: makeActivityId(ActivityKind.TX_SYNC, 'a'),
      source: { type: ActivitySourceType.NATIVE },
    });
    const outGroup = activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'b'), source: { type: ActivitySourceType.NATIVE } });
    modelRef.value = emptyModel([inGroup, outGroup]);

    await useTaskController().cancelGroup(group);
    expect(orchestrator.cancel).toHaveBeenCalledTimes(1);
    expect(orchestrator.cancel).toHaveBeenCalledWith(inGroup.id);
  });

  it('should cancel every cancellable activity on cancelAll', async () => {
    const a = activity({ id: makeActivityId(ActivityKind.PRICES, 'a'), source: { type: ActivitySourceType.NATIVE } });
    const done = activity({
      cancellable: false,
      id: makeActivityId(ActivityKind.PRICES, 'b'),
      source: { type: ActivitySourceType.NATIVE },
      status: ActivityStatus.COMPLETE,
    });
    modelRef.value = emptyModel([a, done]);

    await useTaskController().cancelAll();
    expect(orchestrator.cancel).toHaveBeenCalledTimes(1);
    expect(orchestrator.cancel).toHaveBeenCalledWith(a.id);
  });
});
