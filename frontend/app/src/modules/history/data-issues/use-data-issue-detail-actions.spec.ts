import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { get, set } from '@vueuse/core';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';

const dismiss = vi.fn();
const retry = vi.fn();
const resolveManually = vi.fn();

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({
    dismiss,
    fetchData: vi.fn(),
    resolveManually,
    retry,
  }),
}));

function failure(message: string): { cause: Error; message: string; type: 'conflict' } {
  return { cause: new Error(message), message, type: 'conflict' };
}

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

describe('useDataIssueDetailActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should open the drawer with the selected issue', () => {
    const { modelDrawerOpen, modelSelectedIssue, openDetail } = useDataIssueDetailActions(vi.fn());
    const issue = createIssue();

    openDetail(issue);

    expect(get(modelSelectedIssue)).toStrictEqual(issue);
    expect(get(modelDrawerOpen)).toBe(true);
  });

  it('should dismiss at once, close the drawer and reload', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockResolvedValue(ok(createIssue({ state: IssueState.DISMISSED })));
    const { actionFailure, modelDrawerOpen, onDismiss, openDetail } = useDataIssueDetailActions(reload);
    openDetail(createIssue());

    await onDismiss(1);

    expect(dismiss).toHaveBeenCalledWith(1);
    expect(get(modelDrawerOpen)).toBe(false);
    expect(reload).toHaveBeenCalledOnce();
    expect(get(actionFailure)).toBeUndefined();
  });

  it('should keep a failed dismiss under its title, leave the drawer open and skip the reload', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockResolvedValue(err(failure('nope')));
    const { actionFailure, modelDrawerOpen, onDismiss, openDetail } = useDataIssueDetailActions(reload);
    openDetail(createIssue());

    await onDismiss(1);

    expect(get(actionFailure)).toStrictEqual({ error: failure('nope'), id: 1, title: 'data_issues.action.dismiss.error' });
    expect(get(modelDrawerOpen)).toBe(true);
    expect(reload).not.toHaveBeenCalled();
  });

  it('should drop the last failure when the next action starts', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockResolvedValue(err(failure('nope')));
    retry.mockResolvedValue(ok(createIssue({ state: IssueState.AUTO_REMEDIATING })));
    const { actionFailure, onDismiss, onRetry } = useDataIssueDetailActions(reload);

    await onDismiss(1);
    await onRetry(1);

    expect(get(actionFailure)).toBeUndefined();
  });

  it('should keep a failed retry under its own title', async () => {
    retry.mockResolvedValue(err(failure('conflict')));
    const { actionFailure, onRetry } = useDataIssueDetailActions(vi.fn());

    await onRetry(4);

    expect(get(actionFailure)).toStrictEqual({ error: failure('conflict'), id: 4, title: 'data_issues.action.retry.error' });
  });

  it('should reset the busy flag even if a dismiss rejects', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockRejectedValue(new Error('boom'));
    const { modelActionBusy, onDismiss } = useDataIssueDetailActions(reload);

    await expect(onDismiss(1)).rejects.toThrow('boom');
    expect(get(modelActionBusy)).toBe(false);
  });

  it('should refresh the selected issue after a successful retry', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const updated = createIssue({ state: IssueState.AUTO_REMEDIATING });
    retry.mockResolvedValue(ok(updated));
    const { modelSelectedIssue, onRetry } = useDataIssueDetailActions(reload);

    await onRetry(1);

    expect(get(modelSelectedIssue)).toStrictEqual(updated);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should synchronize an open issue after the list refreshes', async () => {
    const issue = createIssue({ state: IssueState.AUTO_REMEDIATING });
    const issues = ref<DataIssue[]>([issue]);
    const { modelSelectedIssue, openDetail } = useDataIssueDetailActions(vi.fn(), issues);
    openDetail(issue);

    const resolved = createIssue({ state: IssueState.RESOLVED });
    set(issues, [resolved]);
    await nextTick();

    expect(get(modelSelectedIssue)).toStrictEqual(resolved);
  });

  it('should open the resolve dialog on request', () => {
    const { modelResolveOpen, onResolveRequest } = useDataIssueDetailActions(vi.fn());

    onResolveRequest();

    expect(get(modelResolveOpen)).toBe(true);
  });

  it('should no-op resolve confirm when no issue is selected', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const { onResolveConfirm } = useDataIssueDetailActions(reload);

    await onResolveConfirm('note');

    expect(resolveManually).not.toHaveBeenCalled();
    expect(reload).not.toHaveBeenCalled();
  });

  it('should resolve manually with the note, close both dialogs and reload', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    resolveManually.mockResolvedValue(ok(createIssue({ state: IssueState.RESOLVED })));
    const { modelDrawerOpen, modelResolveOpen, onResolveConfirm, onResolveRequest, openDetail } = useDataIssueDetailActions(reload);
    openDetail(createIssue({ id: 7 }));
    onResolveRequest();

    await onResolveConfirm('fixed externally');

    expect(resolveManually).toHaveBeenCalledWith(7, 'fixed externally');
    expect(get(modelResolveOpen)).toBe(false);
    expect(get(modelDrawerOpen)).toBe(false);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should keep a failed resolve for the dialog, which stays open, and skip the reload', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    resolveManually.mockResolvedValue(err(failure('bad state')));
    const { modelResolveOpen, onResolveConfirm, onResolveRequest, openDetail, resolveFailure } = useDataIssueDetailActions(reload);
    openDetail(createIssue({ id: 7 }));
    onResolveRequest();

    await onResolveConfirm(undefined);

    expect(get(resolveFailure)).toStrictEqual(failure('bad state'));
    expect(get(modelResolveOpen)).toBe(true);
    expect(reload).not.toHaveBeenCalled();
  });

  it('should drop a failed resolve when the dialog opens again', async () => {
    resolveManually.mockResolvedValue(err(failure('bad state')));
    const { onResolveConfirm, onResolveRequest, openDetail, resolveFailure } = useDataIssueDetailActions(vi.fn());
    openDetail(createIssue({ id: 7 }));

    await onResolveConfirm(undefined);
    onResolveRequest();

    expect(get(resolveFailure)).toBeUndefined();
  });
});
