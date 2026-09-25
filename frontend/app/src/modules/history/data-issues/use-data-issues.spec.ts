import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { err, ok } from 'plainfp/result';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { isRequestFailure, RequestFailed } from '@/modules/core/api/request-result';
import { createStatusError } from '@/modules/core/api/response-handlers';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';

const listIssues = vi.fn();
const dismissIssue = vi.fn();
const resolveIssueManually = vi.fn();
const retryAutoRemediation = vi.fn();
const setMessage = vi.fn();

vi.mock('@/modules/history/data-issues/api/use-data-issues-api', () => ({
  useDataIssuesApi: (): Record<string, unknown> => ({
    dismissIssue,
    resolveIssueManually,
    retryAutoRemediation,
    listIssues,
  }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

function createIssue(overrides: Partial<DataIssue> = {}): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.NEGATIVE_BALANCE,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state: IssueState.OPEN,
    tsEnd: 1710000000,
    tsStart: 1710000000,
    ...overrides,
  };
}

describe('useDataIssues', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return the collection on a successful fetch', async () => {
    const collection = { data: [createIssue()], found: 1, limit: 10, total: 1 };
    listIssues.mockResolvedValue({ ok: true, value: collection });
    const { fetchData } = useDataIssues();

    const result = await fetchData({ limit: 10, offset: 0 });

    expect(result).toStrictEqual(ok(collection));
  });

  it('should carry the failure with its status for the table to show and file', async () => {
    const cause = createStatusError(500, 'generic', { message: 'boom' });
    listIssues.mockResolvedValue(err({ cause, message: 'generic', type: 'network' }));
    const { fetchData } = useDataIssues();

    const result = await fetchData({ limit: 10, offset: 0 });

    expect(result).toStrictEqual(err(RequestFailed({ cause, message: 'boom', path: undefined, status: 500 })));
  });

  it('should carry a cancelled list request as cancelled, not failed', async () => {
    const cause = new RequestCancelledError('Request was cancelled');
    listIssues.mockResolvedValue(err({ cause, message: 'Request was cancelled', type: 'network' }));
    const { fetchData } = useDataIssues();

    const result = await fetchData({ limit: 10, offset: 0 });

    assert(!result.ok);
    expect(isRequestFailure(result.error)).toBe(false);
  });

  it('should resolve the payload to a plain value before querying', async () => {
    listIssues.mockResolvedValue({ ok: true, value: { data: [], found: 0, limit: 10, total: 0 } });
    const { fetchData } = useDataIssues();

    await fetchData(ref({ limit: 10, offset: 0 }));

    expect(listIssues).toHaveBeenCalledWith({ limit: 10, offset: 0 });
  });

  it('should return the updated issue on a successful dismiss', async () => {
    const updated = createIssue({ state: IssueState.DISMISSED });
    dismissIssue.mockResolvedValue({ ok: true, value: updated });
    const { dismiss } = useDataIssues();

    const result = await dismiss(1);

    expect(dismissIssue).toHaveBeenCalledWith(1);
    expect(result).toStrictEqual(updated);
    expect(setMessage).not.toHaveBeenCalled();
  });

  it('should set an error message and return undefined when dismiss fails', async () => {
    dismissIssue.mockResolvedValue({ error: { message: 'nope' }, ok: false });
    const { dismiss } = useDataIssues();

    const result = await dismiss(1);

    expect(result).toBeUndefined();
    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
      description: 'nope',
      success: false,
    }));
  });

  it('should pass the note through when resolving manually', async () => {
    resolveIssueManually.mockResolvedValue({ ok: true, value: createIssue({ state: IssueState.RESOLVED }) });
    const { resolveManually } = useDataIssues();

    await resolveManually(3, 'fixed externally');

    expect(resolveIssueManually).toHaveBeenCalledWith(3, 'fixed externally');
  });

  it('should set an error message when a manual resolve fails', async () => {
    resolveIssueManually.mockResolvedValue({ error: { message: 'bad state' }, ok: false });
    const { resolveManually } = useDataIssues();

    const result = await resolveManually(3);

    expect(result).toBeUndefined();
    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'bad state' }));
  });

  it('should return the updated issue on a successful retry', async () => {
    const updated = createIssue({ state: IssueState.AUTO_REMEDIATING });
    retryAutoRemediation.mockResolvedValue({ ok: true, value: updated });
    const { retry } = useDataIssues();

    const result = await retry(9);

    expect(retryAutoRemediation).toHaveBeenCalledWith(9);
    expect(result).toStrictEqual(updated);
  });

  it('should set an error message when a retry fails', async () => {
    retryAutoRemediation.mockResolvedValue({ error: { message: 'conflict' }, ok: false });
    const { retry } = useDataIssues();

    const result = await retry(9);

    expect(result).toBeUndefined();
    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'conflict' }));
  });
});
