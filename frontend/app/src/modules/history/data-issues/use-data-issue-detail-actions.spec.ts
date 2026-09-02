import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { get, set } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';

const dismiss = vi.fn();
const retry = vi.fn();
const resolveManually = vi.fn();
const show = vi.fn<(message: unknown, onConfirm: () => Promise<void>) => void>();

vi.mock('@/modules/history/data-issues/use-data-issues', () => ({
  useDataIssues: (): Record<string, unknown> => ({
    dismiss,
    fetchData: vi.fn(),
    resolveManually,
    retry,
  }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

/** Runs the onConfirm callback the composable handed to the confirm dialog. */
async function confirmDismiss(): Promise<void> {
  const onConfirm = show.mock.calls.at(-1)?.[1];
  if (!onConfirm)
    throw new Error('confirm dialog was not shown');
  await onConfirm();
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

  it('should ask for confirmation before dismissing and not dismiss until confirmed', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const { onDismiss } = useDataIssueDetailActions(reload);

    await onDismiss(1);

    expect(show).toHaveBeenCalledOnce();
    expect(dismiss).not.toHaveBeenCalled();
    expect(reload).not.toHaveBeenCalled();
  });

  it('should close the drawer and reload after a confirmed dismiss', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockResolvedValue(createIssue({ state: IssueState.DISMISSED }));
    const { modelDrawerOpen, onDismiss, openDetail } = useDataIssueDetailActions(reload);
    openDetail(createIssue());

    await onDismiss(1);
    await confirmDismiss();

    expect(dismiss).toHaveBeenCalledWith(1);
    expect(get(modelDrawerOpen)).toBe(false);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should keep the drawer open and skip reload when a confirmed dismiss fails', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockResolvedValue(undefined);
    const { modelDrawerOpen, onDismiss, openDetail } = useDataIssueDetailActions(reload);
    openDetail(createIssue());

    await onDismiss(1);
    await confirmDismiss();

    expect(get(modelDrawerOpen)).toBe(true);
    expect(reload).not.toHaveBeenCalled();
  });

  it('should reset the busy flag even if a confirmed dismiss rejects', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    dismiss.mockRejectedValue(new Error('boom'));
    const { modelActionBusy, onDismiss } = useDataIssueDetailActions(reload);

    await onDismiss(1);
    await expect(confirmDismiss()).rejects.toThrow('boom');
    expect(get(modelActionBusy)).toBe(false);
  });

  it('should refresh the selected issue after a successful retry', async () => {
    const reload = vi.fn().mockResolvedValue(undefined);
    const updated = createIssue({ state: IssueState.AUTO_REMEDIATING });
    retry.mockResolvedValue(updated);
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
    resolveManually.mockResolvedValue(createIssue({ state: IssueState.RESOLVED }));
    const { modelDrawerOpen, modelResolveOpen, onResolveConfirm, onResolveRequest, openDetail } = useDataIssueDetailActions(reload);
    openDetail(createIssue({ id: 7 }));
    onResolveRequest();

    await onResolveConfirm('fixed externally');

    expect(resolveManually).toHaveBeenCalledWith(7, 'fixed externally');
    expect(get(modelResolveOpen)).toBe(false);
    expect(get(modelDrawerOpen)).toBe(false);
    expect(reload).toHaveBeenCalledOnce();
  });
});
