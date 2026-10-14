import { runSpecWith } from '@test/utils/mocks/native-task';
import { withSetup } from '@test/utils/with-setup';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { useStakingRows } from '@/modules/staking/use-staking-rows';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

const runTask = vi.hoisted(() => vi.fn());
const submitTask = vi.hoisted(() => vi.fn());

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { submitTask: typeof submitTask } => ({ submitTask }),
}));

const TestResponseSchema = z.object({ failed: z.array(z.string()), rows: z.array(z.string()) });

type TestResponse = z.infer<typeof TestResponseSchema>;

const query = vi.fn<() => Promise<{ taskId: number }>>();

function setup(): ReturnType<typeof useStakingRows<TestResponse, string, number>> {
  return withSetup(() => useStakingRows<TestResponse, string, number>({
    parse: result => TestResponseSchema.parse(result),
    part: ActivityPart.SOLANA,
    query,
    toRows: response => response.rows,
    toTotal: rows => rows.length,
  })).result;
}

describe('modules/staking/useStakingRows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    query.mockResolvedValue({ taskId: 1 });
    submitTask.mockImplementation(runSpecWith(runTask));
    runTask.mockImplementation(async (task: () => Promise<unknown>) => {
      await task();
      return ok({ failed: [], rows: ['a', 'b'] });
    });
  });

  it('should submit the query as a staking task identified by its part', async () => {
    await setup().refresh();

    expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({
      id: `${ActivityKind.STAKING}:${ActivityPart.SOLANA}`,
      kind: ActivityKind.STAKING,
    }));
    expect(query).toHaveBeenCalledOnce();
  });

  it('should expose the rows of the task result and the total derived from them', async () => {
    const result = setup();

    await result.refresh();

    expect(get(result.rows)).toEqual(['a', 'b']);
    expect(get(result.total)).toBe(2);
  });

  it('should take the rows from the outcome when the submit joins a run already in flight', async () => {
    submitTask.mockResolvedValue(ok({ failed: ['0xBad'], rows: ['joined'] }));
    const result = setup();

    await result.refresh();

    expect(get(result.rows)).toEqual(['joined']);
    expect(get(result.failedAddresses)).toEqual(['0xBad']);
    expect(query).not.toHaveBeenCalled();
  });

  it('should expose the addresses that could not be loaded', async () => {
    runTask.mockResolvedValue(ok({ failed: ['0xBad'], rows: ['a'] }));
    const result = setup();

    await result.refresh();

    expect(get(result.failedAddresses)).toEqual(['0xBad']);
  });

  it('should keep the rows of the last successful query when a later one fails', async () => {
    const result = setup();
    await result.refresh();

    runTask.mockResolvedValue(err(TaskFailed({ message: 'api down' })));
    await result.refresh();

    expect(get(result.rows)).toEqual(['a', 'b']);
  });

  it('should count as loaded only once a query has succeeded', async () => {
    runTask.mockResolvedValue(err(TaskFailed({ message: 'api down' })));
    const result = setup();

    await result.refresh();
    expect(get(result.loaded)).toBe(false);

    runTask.mockResolvedValue(ok({ failed: [], rows: [] }));
    await result.refresh();
    expect(get(result.loaded)).toBe(true);
  });

  it('should be loading only while a query is in flight', async () => {
    const result = setup();

    const pending = result.refresh();
    expect(get(result.loading)).toBe(true);

    await pending;
    expect(get(result.loading)).toBe(false);
  });
});
