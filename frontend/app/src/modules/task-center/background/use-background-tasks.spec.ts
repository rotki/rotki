import type { Result } from 'plainfp/result';
import type { BackgroundTask, BackgroundTaskStatusData } from './background-task-types';
import type { TaskError } from '@/modules/core/tasks/task-result';
import type { NativeActivitySpec, TaskOutcome } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { flushPromises } from '@vue/test-utils';
import { hasTag } from 'plainfp/tagged';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { BACKGROUND_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind } from '@/modules/task-center/core/types';

const { specs, submitTask } = vi.hoisted(() => {
  const specs: NativeActivitySpec[] = [];
  return {
    specs,
    submitTask: vi.fn(async (spec: NativeActivitySpec): Promise<TaskOutcome> => {
      specs.push(spec);
      return spec.run(createMock());
    }),
  };
});

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { submitTask: typeof submitTask } => ({ submitTask }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): { getChainName: (chain: string) => string } => ({ getChainName: chain => `chain ${chain}` }),
}));

const transactions: BackgroundTask = {
  id: 7,
  kind: 'evm_transactions',
  name: 'Query ethereum transactions for 0xabc',
  startedAt: 1,
  subject: { address: '0xabc', chain: 'eth' },
};

function status(task: BackgroundTask, update: Pick<BackgroundTaskStatusData, 'status' | 'error'>): BackgroundTaskStatusData {
  return { ...task, ...update };
}

/** The outcome a submitted mirror's run settled with, once it has. */
async function outcomeOf(index: number): Promise<Result<void, TaskError> | undefined> {
  const spec = specs[index];
  assert(spec);
  let settled: Result<void, TaskError> | undefined;
  startOutcome(spec, (outcome) => {
    settled = outcome;
  });
  await flushPromises();
  return settled;
}

function startOutcome(spec: NativeActivitySpec, onSettled: (outcome: Result<void, TaskError>) => void): void {
  spec.run(createMock()).then(onSettled, () => {});
}

async function setup(): Promise<ReturnType<typeof import('./use-background-tasks').useBackgroundTasks>> {
  const { useBackgroundTasks } = await import('./use-background-tasks');
  return useBackgroundTasks();
}

describe('useBackgroundTasks', () => {
  beforeEach(() => {
    vi.resetModules();
    specs.length = 0;
    submitTask.mockClear();
  });

  it('should mirror a started task as a background activity that is not interruptible', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { status: 'started' }));

    expect(specs).toHaveLength(1);
    expect(specs[0]).toMatchObject({
      id: 'background-task:evm_transactions:7:eth:0xabc',
      interruptible: false,
      kind: ActivityKind.BACKGROUND_TASK,
      lane: BACKGROUND_LANE,
      subtitle: { key: 'task_center.activity.background_task.evm_transactions', params: { address: '0xabc' } },
      title: 'task_center.background_task.evm_transactions',
    });
  });

  it('should keep the mirror running until the task ends, then complete it', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    expect(await outcomeOf(0)).toBeUndefined();

    onStatus(status(transactions, { status: 'finished' }));
    expect(await outcomeOf(0)).toEqual({ ok: true, value: undefined });
  });

  it('should fail the mirror with the error of a failure treated as an error', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    onStatus(status(transactions, { error: 'etherscan is down', status: 'failed' }));

    const outcome = await outcomeOf(0);
    assert(outcome && !outcome.ok);
    expect(hasTag(outcome.error, 'TaskFailed')).toBe(true);
    expect(outcome.error.message).toBe('etherscan is down');
  });

  it('should complete the mirror of a failure the backend does not treat as an error', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    onStatus(status(transactions, { status: 'failed' }));

    expect(await outcomeOf(0)).toEqual({ ok: true, value: undefined });
  });

  it('should settle the mirror of a cancelled task as cancelled by the backend', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    onStatus(status(transactions, { status: 'cancelled' }));

    const outcome = await outcomeOf(0);
    assert(outcome && !outcome.ok);
    expect(hasTag(outcome.error, 'BackendCancelled')).toBe(true);
  });

  it('should mirror a task once however many times it is announced', async () => {
    const { onStatus, resync } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    onStatus(status(transactions, { status: 'started' }));
    resync([transactions], Date.now() + 1);

    expect(submitTask).toHaveBeenCalledOnce();
  });

  it('should give upkeep of kind other no row while it runs, and a failed row named by the backend when it fails', async () => {
    const upkeep: BackgroundTask = { id: 9, kind: 'other', name: 'Update ilk cache', startedAt: 1, subject: {} };
    const { onStatus } = await setup();
    onStatus(status(upkeep, { status: 'started' }));
    onStatus(status(upkeep, { status: 'finished' }));
    expect(submitTask).not.toHaveBeenCalled();

    onStatus(status(upkeep, { error: 'node unreachable', status: 'failed' }));
    expect(specs[0]?.subtitle).toBe('Update ilk cache');
    const outcome = await outcomeOf(0);
    assert(outcome && !outcome.ok);
    expect(outcome.error.message).toBe('node unreachable');
  });

  it('should show a failure whose start was never seen, as a held message delivers it', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { error: 'etherscan is down', status: 'failed' }));

    expect(submitTask).toHaveBeenCalledOnce();
    const outcome = await outcomeOf(0);
    assert(outcome && !outcome.ok);
  });

  it('should ignore an end with no error for a task it never mirrored', async () => {
    const { onStatus } = await setup();
    onStatus(status(transactions, { status: 'finished' }));

    expect(submitTask).not.toHaveBeenCalled();
  });

  it('should mirror a running task the periodic data lists and the messages missed', async () => {
    const { resync } = await setup();
    resync([transactions], Date.now());

    expect(specs[0]?.id).toBe('background-task:evm_transactions:7:eth:0xabc');
    expect(await outcomeOf(0)).toBeUndefined();
  });

  it('should complete a mirror whose task the periodic data no longer lists', async () => {
    vi.useFakeTimers({ now: 1_000 });
    const { onStatus, resync } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    resync([], 2_000);
    vi.useRealTimers();

    expect(await outcomeOf(0)).toEqual({ ok: true, value: undefined });
  });

  it('should leave a mirror created after the periodic request was sent', async () => {
    vi.useFakeTimers({ now: 3_000 });
    const { onStatus, resync } = await setup();
    onStatus(status(transactions, { status: 'started' }));
    resync([], 2_000);
    vi.useRealTimers();

    expect(await outcomeOf(0)).toBeUndefined();
  });
});
