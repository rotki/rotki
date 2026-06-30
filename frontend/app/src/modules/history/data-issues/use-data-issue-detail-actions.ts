import type { Ref } from 'vue';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
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
 *
 * The returned refs use the `model` prefix because they are two-way bindings the
 * consumer drives via `v-model` / mutates, which the `composable-return-readonly`
 * lint rule treats as writable-by-convention.
 */
export function useDataIssueDetailActions(
  reload: () => Promise<void>,
): UseDataIssueDetailActionsReturn {
  const { dismiss, resolveManually, retry } = useDataIssues();

  const modelSelectedIssue = ref<DataIssue>();
  const modelDrawerOpen = shallowRef<boolean>(false);
  const modelResolveOpen = shallowRef<boolean>(false);
  const modelActionBusy = shallowRef<boolean>(false);

  function openDetail(issue: DataIssue): void {
    set(modelSelectedIssue, issue);
    set(modelDrawerOpen, true);
  }

  async function onDismiss(id: number): Promise<void> {
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
