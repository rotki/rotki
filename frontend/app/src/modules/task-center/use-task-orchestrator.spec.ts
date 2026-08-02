import type { Result } from 'plainfp/result';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { get } from '@vueuse/core';
import { describe, expect, it } from 'vitest';
import { ActivityKind, ActivityStatus, makeActivityId } from './core/types';
import { useTaskOrchestrator } from './use-task-orchestrator';

const flush = async (): Promise<void> => new Promise(resolve => setTimeout(resolve, 0));

describe('useTaskOrchestrator', () => {
  it('should expose a reactive snapshot that tracks the orchestrator', async () => {
    const orchestrator = useTaskOrchestrator();
    let settle!: (result: Result<unknown, TaskError>) => void;

    const id = orchestrator.submit({
      id: makeActivityId(ActivityKind.PRICES, 'reactive-test'),
      kind: ActivityKind.PRICES,
      run: async () => new Promise<Result<unknown, TaskError>>((resolve) => {
        settle = resolve;
      }),
      title: 'prices',
    });

    const running = get(orchestrator.activities).find(activity => activity.id === id);
    expect(running?.status).toBe(ActivityStatus.RUNNING);

    settle({ ok: true, value: undefined });
    await flush();

    const done = get(orchestrator.activities).find(activity => activity.id === id);
    expect(done?.status).toBe(ActivityStatus.COMPLETE);
  });

  it('should hide ephemeral activities from the reactive projection but still track them', async () => {
    const orchestrator = useTaskOrchestrator();
    let settle!: (result: Result<unknown, TaskError>) => void;

    const id = orchestrator.submit({
      ephemeral: true,
      id: makeActivityId(ActivityKind.SESSION, 'login'),
      kind: ActivityKind.SESSION,
      run: async () => new Promise<Result<unknown, TaskError>>((resolve) => {
        settle = resolve;
      }),
      title: 'login',
    });

    // Excluded from the render model...
    expect(get(orchestrator.activities).some(activity => activity.id === id)).toBe(false);
    // ...but the orchestrator still tracks it internally (scheduling, status queries).
    expect(orchestrator.snapshot().some(activity => activity.id === id)).toBe(true);
    expect(orchestrator.statusOf(ActivityKind.SESSION, 'login').running).toBe(true);

    settle({ ok: true, value: undefined });
    await flush();

    expect(get(orchestrator.activities).some(activity => activity.id === id)).toBe(false);
    expect(orchestrator.statusOf(ActivityKind.SESSION, 'login').everCompleted).toBe(true);
  });
});
