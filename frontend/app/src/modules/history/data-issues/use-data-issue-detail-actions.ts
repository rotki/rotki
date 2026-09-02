import type { MaybeRefOrGetter, Ref } from 'vue';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';

interface UseDataIssueDetailActionsReturn {
  modelSelectedIssue: Ref<DataIssue | undefined>;
  modelDrawerOpen: Ref<boolean>;
  modelResolveOpen: Ref<boolean>;
  modelActionBusy: Ref<boolean>;
  openDetail: (issue: DataIssue) => void;
  onDismiss: (id: number) => Promise<void>;
  onRetry: (id: number) => Promise<void>;
  onResolveRequest: () => void;
  onResolveConfirm: (note: string | undefined) => Promise<void>;
}

/**
 * Detail-drawer and per-issue action orchestration shared by the inbox panel and
 * the full page. Owns the selected issue, the drawer/resolve-dialog visibility,
 * and a busy flag; each successful action triggers the caller-supplied `reload`
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
  const { show } = useConfirmStore();

  const modelSelectedIssue = ref<DataIssue>();
  const modelDrawerOpen = shallowRef<boolean>(false);
  const modelResolveOpen = shallowRef<boolean>(false);
  const modelActionBusy = shallowRef<boolean>(false);

  function openDetail(issue: DataIssue): void {
    set(modelSelectedIssue, issue);
    set(modelDrawerOpen, true);
  }

  /**
   * Prompts for confirmation, then hides the issue and stops its auto-remediation.
   *
   * @remarks
   * The prompt lives at this choke point rather than at each call site, so the drawer, the panel
   * cards and the table's quick action all inherit it. The returned promise settles once the
   * prompt has been raised, not once the dismissal has gone through.
   */
  async function onDismiss(id: number): Promise<void> {
    show(
      {
        message: t('data_issues.action.dismiss.confirm.message'),
        title: t('data_issues.action.dismiss.confirm.title'),
        type: 'warning',
      },
      async () => {
        set(modelActionBusy, true);
        try {
          const updated = await dismiss(id);
          if (updated) {
            set(modelDrawerOpen, false);
            await reload();
          }
        }
        finally {
          set(modelActionBusy, false);
        }
      },
    );
  }

  async function onRetry(id: number): Promise<void> {
    set(modelActionBusy, true);
    try {
      const updated = await retry(id);
      if (updated) {
        set(modelSelectedIssue, updated);
        await reload();
      }
    }
    finally {
      set(modelActionBusy, false);
    }
  }

  function onResolveRequest(): void {
    set(modelResolveOpen, true);
  }

  async function onResolveConfirm(note: string | undefined): Promise<void> {
    const issue = get(modelSelectedIssue);
    if (!issue)
      return;
    set(modelActionBusy, true);
    try {
      const updated = await resolveManually(issue.id, note);
      if (updated) {
        set(modelResolveOpen, false);
        set(modelDrawerOpen, false);
        await reload();
      }
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
    modelActionBusy,
    modelDrawerOpen,
    modelResolveOpen,
    modelSelectedIssue,
    onDismiss,
    onResolveConfirm,
    onResolveRequest,
    onRetry,
    openDetail,
  };
}
