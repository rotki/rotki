import type { RotkiApi } from '@/modules/core/api/rotki-api';
import type { Collection } from '@/modules/core/common/collection';
import { Priority } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestCancelled, type RequestError, RequestFailed } from '@/modules/core/api/request-result';
import { useTableData } from '@/modules/core/table/use-table-data';
import '@test/i18n';

const { cancelByTag, notifyError } = vi.hoisted(() => ({
  cancelByTag: vi.fn<(tag: string) => void>(),
  notifyError: vi.fn(),
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: createMock<RotkiApi>({ cancelByTag: (tag: string): void => cancelByTag(tag) }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): Record<string, unknown> => ({ notifyError }),
}));

const page: Collection<{ id: number }> = { data: [{ id: 1 }], found: 1, limit: 10, total: 1 };

describe('useTableData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should file one quiet drawer entry for a failed response', async () => {
    const failure = RequestFailed({ cause: undefined, message: 'Report 3 does not exist', path: '/api/1/reports/3', status: 409 });
    const { error, refetch } = useTableData(vi.fn().mockResolvedValue(err(failure)), () => ({}));

    await refetch();

    expect(get(error)).toBe(failure);
    expect(notifyError).toHaveBeenCalledExactlyOnceWith(
      'error.generic.title',
      expect.stringContaining('Report 3 does not exist'),
      { priority: Priority.NORMAL },
    );
  });

  it('should show a failure without a status inline only', async () => {
    const failure = RequestFailed({ cause: new TypeError('fetch failed'), message: 'fetch failed' });
    const { error, refetch } = useTableData(vi.fn().mockResolvedValue(err(failure)), () => ({}));

    await refetch();

    expect(get(error)).toBe(failure);
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should neither show nor file a cancelled fetch, and keep the rows it had', async () => {
    const requestData = vi.fn().mockResolvedValueOnce(ok(page));
    const { collection, error, isLoading, refetch } = useTableData(requestData, () => ({}));
    await refetch();

    requestData.mockResolvedValueOnce(err(RequestCancelled({ message: 'Request was cancelled' })));
    await refetch();

    expect(get(collection)).toBe(page);
    expect(get(error)).toBeUndefined();
    expect(get(isLoading)).toBe(false);
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should drop the previous rows when a refetch fails, so the table shows the reason', async () => {
    const failure = RequestFailed({ cause: new TypeError('fetch failed'), message: 'fetch failed' });
    const requestData = vi.fn().mockResolvedValueOnce(ok(page)).mockResolvedValueOnce(err(failure));
    const { collection, error, refetch } = useTableData(requestData, () => ({}));
    await refetch();

    await refetch();

    expect(get(collection).data).toEqual([]);
    expect(get(error)).toBe(failure);
  });

  it('should stop loading and show the failure when the fetch throws', async () => {
    const thrown = new Error('cannot map row');
    const { error, isLoading, refetch } = useTableData(vi.fn().mockRejectedValue(thrown), () => ({}));

    await refetch();

    expect(get(isLoading)).toBe(false);
    expect(get(error)).toMatchObject({ cause: thrown, message: 'cannot map row' });
  });

  it('should keep the newest fetch when an older one settles after it', async () => {
    let settleStale: (result: Result<Collection<{ id: number }>, RequestError>) => void = () => {};
    const stale = new Promise<Result<Collection<{ id: number }>, RequestError>>((resolve) => {
      settleStale = resolve;
    });
    const newer: Collection<{ id: number }> = { data: [{ id: 2 }], found: 1, limit: 10, total: 1 };
    const requestData = vi.fn()
      .mockReturnValueOnce(stale)
      .mockResolvedValueOnce(ok(newer));
    const { collection, error, isLoading, refetch } = useTableData(requestData, () => ({}));

    const first = refetch();
    await refetch();
    settleStale(err(RequestFailed({ cause: undefined, message: 'stale', status: 500 })));
    await first;

    expect(get(collection)).toBe(newer);
    expect(get(error)).toBeUndefined();
    expect(get(isLoading)).toBe(false);
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should cancel the tagged requests in flight before fetching again', async () => {
    const { refetch } = useTableData(vi.fn().mockResolvedValue(ok(page)), () => ({}), 'history-events-groups');

    await refetch();

    expect(cancelByTag).toHaveBeenCalledExactlyOnceWith('history-events-groups');
  });
});
