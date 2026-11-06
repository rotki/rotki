import type { ResultAsync } from 'plainfp/result-async';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { DataIssueError } from '@/modules/history/data-issues/types';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

interface UseDataIssueDetailActionsReturn {
  modelSelectedIssue: Ref<DataIssue | undefined>;
  modelDrawerOpen: Ref<boolean>;
  modelResolveOpen: Ref<boolean>;
  modelActionBusy: Ref<boolean>;
  /** Why the last dismiss or retry failed, on whichever issue; cleared when the next action starts. */
  actionFailure: Readonly<Ref<NamedFailure | undefined>>;
  /** {@link UseDataIssueDetailActionsReturn.actionFailure} when it is the selected issue's own. */
  selectedIssueFailure: ComputedRef<NamedFailure | undefined>;
  /** Why the last manual resolve failed, for the resolve dialog; cleared when it opens or resolves again. */
  resolveFailure: Readonly<Ref<DataIssueError | undefined>>;
  openDetail: (issue: DataIssue) => void;
  onDismiss: (id: number) => Promise<void>;
  onRetry: (id: number) => Promise<void>;
  onResolveRequest: () => void;
  onResolveConfirm: (note: string | undefined) => Promise<void>;
}

/**
 * Detail-drawer and per-issue action orchestration shared by the inbox panel and
 * the full page. Owns the selected issue, the drawer/resolve-dialog visibility,
 * a busy flag and the last failure; each successful action triggers the caller-supplied `reload`
 * so both the list and the badge summary refresh from a single place.
 * The selected issue is synchronized from `issues` after polling or an explicit refresh.
 *
 * The returned refs use the `model` prefix because they are two-way bindings the
 * consumer drives via `v-model` / mutates, which the `composable-return-readonly`
 * lint rule treats as writable-by-convention.
 */
export function useDataIssueDetailActions(
  reload: () => Promise<void>,
  issues: MaybeRefOrGetter<DataIssue[]> = () => [],
): UseDataIssueDetailActionsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { dismiss, resolveManually, retry } = useDataIssues();

  const modelSelectedIssue = ref<DataIssue>();
  const modelDrawerOpen = shallowRef<boolean>(false);
  const modelResolveOpen = shallowRef<boolean>(false);
  const modelActionBusy = shallowRef<boolean>(false);
  const { clear: clearActionFailure, failure: actionFailure, report: reportActionFailure } = useFailureSlot();
  /** The issue the last failed action ran on, kept beside the failure rather than inside it. */
  const failedIssueId = shallowRef<number>();
  const selectedIssueFailure = computed<NamedFailure | undefined>(() =>
    get(failedIssueId) === get(modelSelectedIssue)?.id ? get(actionFailure) : undefined);
  const resolveFailure = shallowRef<DataIssueError>();

  function openDetail(issue: DataIssue): void {
    set(modelSelectedIssue, issue);
    set(modelDrawerOpen, true);
  }

  /**
   * Runs one action on an issue, keeping its failure under `title`.
   *
   * @remarks
   * Stays busy through `onUpdated`, so the buttons stay disabled until the reload has landed.
   */
  async function runAction(
    id: number,
    title: string,
    action: ResultAsync<DataIssue, DataIssueError>,
    onUpdated: (updated: DataIssue) => Promise<void>,
  ): Promise<void> {
    set(modelActionBusy, true);
    clearActionFailure();
    set(failedIssueId, undefined);
    try {
      const result = await action;
      if (result.ok) {
        await onUpdated(result.value);
      }
      else {
        reportActionFailure(title, result.error);
        set(failedIssueId, id);
      }
    }
    finally {
      set(modelActionBusy, false);
    }
  }

  /**
   * Hides the issue and stops its auto-remediation.
   *
   * @remarks
   * Runs at once: each Dismiss button asks beside itself before emitting.
   */
  async function onDismiss(id: number): Promise<void> {
    await runAction(id, t('data_issues.action.dismiss.error'), dismiss(id), async () => {
      set(modelDrawerOpen, false);
      await reload();
    });
  }

  async function onRetry(id: number): Promise<void> {
    await runAction(id, t('data_issues.action.retry.error'), retry(id), async (updated) => {
      set(modelSelectedIssue, updated);
      await reload();
    });
  }

  function onResolveRequest(): void {
    set(resolveFailure, undefined);
    set(modelResolveOpen, true);
  }

  async function onResolveConfirm(note: string | undefined): Promise<void> {
    const issue = get(modelSelectedIssue);
    if (!issue)
      return;
    set(modelActionBusy, true);
    set(resolveFailure, undefined);
    try {
      const result = await resolveManually(issue.id, note);
      if (!result.ok) {
        set(resolveFailure, result.error);
        return;
      }
      set(modelResolveOpen, false);
      set(modelDrawerOpen, false);
      await reload();
    }
    finally {
      set(modelActionBusy, false);
    }
  }

  watch(() => toValue(issues), (updatedIssues) => {
    const selected = get(modelSelectedIssue);
    if (!selected)
      return;

    const updated = updatedIssues.find(issue => issue.id === selected.id);
    if (updated)
      set(modelSelectedIssue, updated);
  });

  return {
    actionFailure,
    modelActionBusy,
    modelDrawerOpen,
    modelResolveOpen,
    modelSelectedIssue,
    onDismiss,
    onResolveConfirm,
    onResolveRequest,
    onRetry,
    openDetail,
    resolveFailure: shallowReadonly(resolveFailure),
    selectedIssueFailure,
  };
}
