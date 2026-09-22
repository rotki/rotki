import type { ResultAsync } from 'plainfp/result-async';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { ok, type Result } from 'plainfp/result';
import { afterEach, describe, expect, it } from 'vitest';
import { effectScope } from 'vue';
import { ActivityKind, makeActivityId } from './core/types';
import { type ActivityAddress, useLiveActivityEntries } from './use-live-activity-entries';
import { useTaskOrchestrator } from './use-task-orchestrator';

const flush = async (): Promise<void> => new Promise(resolve => setTimeout(resolve, 0));

let scope: ReturnType<typeof effectScope> | undefined;

function entries(): ReturnType<typeof useLiveActivityEntries<string>> {
  scope = effectScope();
  return scope.run(() => useLiveActivityEntries<string>())!;
}

/** Submits an activity that runs until `finish` is called. */
function running(name: string): { address: ActivityAddress; finish: () => void } {
  const { submit } = useTaskOrchestrator();
  let finish!: () => void;
  submit({
    id: makeActivityId(ActivityKind.OTHER, name),
    kind: ActivityKind.OTHER,
    run: async (): ResultAsync<void, TaskError> => new Promise<Result<void, TaskError>>((resolve) => {
      finish = (): void => resolve(ok(undefined));
    }),
    title: name,
  });
  return { address: { kind: ActivityKind.OTHER, parts: [name] }, finish };
}

describe('useLiveActivityEntries', () => {
  afterEach(() => {
    scope?.stop();
  });

  it('should keep an entry while its activity runs', () => {
    const { isLive, read, write } = entries();
    const { address, finish } = running('kept');

    write(address, 'range');

    expect(isLive(address)).toBe(true);
    expect(read(address)).toBe('range');
    finish();
  });

  it('should drop the entry once its activity settles, so the next run starts from nothing', async () => {
    const { isLive, read, write } = entries();
    const { address, finish } = running('settles');
    write(address, 'range');

    finish();
    await flush();

    expect(isLive(address)).toBe(false);
    expect(read(address)).toBeUndefined();
  });

  it('should call an activity that was never submitted not live', () => {
    const { isLive } = entries();

    expect(isLive({ kind: ActivityKind.OTHER, parts: ['never'] })).toBe(false);
  });

  it('should stop pruning once its scope is gone', async () => {
    const { read, write } = entries();
    const { address, finish } = running('orphaned');
    write(address, 'range');

    scope?.stop();
    finish();
    await flush();

    expect(read(address)).toBe('range');
  });
});
