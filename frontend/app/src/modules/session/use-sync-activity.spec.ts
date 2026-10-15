import { isErr, isOk, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSyncActivity } from '@/modules/session/use-sync-activity';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';

const manualSyncActive = ref<boolean>(false);
const reportProgress = vi.fn();
const outcomes: Promise<Result<unknown, unknown>>[] = [];
const submitTask = vi.fn(async (spec: { run: () => Promise<Result<unknown, unknown>> }) => {
  const outcome = spec.run();
  outcomes.push(outcome);
  return outcome;
});

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({ reportProgress, submitTask })),
}));

vi.mock('@/modules/session/use-session-sync', () => ({
  useSync: vi.fn(() => ({ manualSyncActive })),
}));

const manualId = makeActivityId(ActivityKind.SYNC);
const automaticId = makeActivityId(ActivityKind.SYNC, 'automatic');

describe('useSyncActivity', () => {
  let activity: ReturnType<typeof useSyncActivity>;

  beforeEach(() => {
    vi.clearAllMocks();
    outcomes.length = 0;
    set(manualSyncActive, false);
    activity = useSyncActivity();
  });

  it('should feed upload progress into the manual sync row', () => {
    set(manualSyncActive, true);

    activity.onProgress({ currentChunk: 2, totalChunks: 5, type: 'uploading' });

    expect(submitTask).not.toHaveBeenCalled();
    expect(reportProgress).toHaveBeenCalledWith(manualId, { current: 2, total: 5 });
  });

  it('should ignore the result of a manual sync', () => {
    set(manualSyncActive, true);

    activity.onResult({ actionable: false, message: 'refused', uploaded: false });

    expect(submitTask).not.toHaveBeenCalled();
  });

  it('should open one automatic row and settle it on success', async () => {
    activity.onProgress({ type: 'compressing' });
    activity.onProgress({ currentChunk: 1, totalChunks: 3, type: 'uploading' });

    expect(submitTask).toHaveBeenCalledOnce();
    expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({ id: automaticId }));
    expect(reportProgress).toHaveBeenCalledOnce();
    expect(reportProgress).toHaveBeenCalledWith(automaticId, { current: 1, total: 3 });

    activity.onResult({ actionable: false, message: null, uploaded: true });

    expect(isOk(await outcomes[0])).toBe(true);
  });

  it('should open and fail an automatic row when the upload is refused', async () => {
    activity.onResult({ actionable: true, message: 'too large', uploaded: false });

    expect(submitTask).toHaveBeenCalledOnce();
    const outcome = await outcomes[0];
    expect(isErr(outcome)).toBe(true);
    expect(outcome).toMatchObject({ error: { message: 'too large' } });
  });

  it('should open a fresh automatic row for the next upload', async () => {
    activity.onProgress({ currentChunk: 1, totalChunks: 1, type: 'uploading' });
    activity.onResult({ actionable: false, message: null, uploaded: true });
    activity.onProgress({ currentChunk: 1, totalChunks: 1, type: 'uploading' });

    expect(submitTask).toHaveBeenCalledTimes(2);
    expect(isOk(await outcomes[0])).toBe(true);
  });
});
