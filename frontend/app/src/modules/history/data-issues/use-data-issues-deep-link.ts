import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { omit } from 'es-toolkit';
import { type MaybeRefOrGetter, readonly, ref, type Ref, toValue, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

interface UseDataIssuesDeepLinkOptions {
  /** Whether `?issue=` deep-linking is active on the current surface. */
  readonly enabled: MaybeRefOrGetter<boolean>;
  /** Tracks drawer visibility so closing it strips `?issue=` from the URL. */
  readonly drawerOpen: Ref<boolean>;
  /** Loads a single issue by id independently of table filters. */
  readonly fetchIssue: (id: number) => Promise<{ issue?: DataIssue; error?: string }>;
  /** Opens the detail drawer for the resolved issue. */
  readonly openDetail: (issue: DataIssue) => void;
}

interface UseDataIssuesDeepLinkReturn {
  readonly clearIssueQuery: () => Promise<void>;
  readonly deepLinkError: Readonly<Ref<string | undefined>>;
}

/**
 * Opens a specific issue from `?issue=<id>` on the full data-issues page and clears the query
 * parameter once the drawer closes so subsequent reloads do not reopen a dismissed link.
 */
export function useDataIssuesDeepLink(options: UseDataIssuesDeepLinkOptions): UseDataIssuesDeepLinkReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const currentRoute = router.currentRoute;

  const deepLinkError = ref<string>();
  const deepLinkIssueId = ref<number>();

  async function clearIssueQuery(): Promise<void> {
    if (get(currentRoute).query.issue === undefined)
      return;

    const query = omit(get(currentRoute).query, ['issue']);
    set(deepLinkError, undefined);
    set(deepLinkIssueId, undefined);
    await router.replace({ query });
  }

  async function openIssueFromQuery(): Promise<void> {
    if (!toValue(options.enabled))
      return;

    const raw = get(currentRoute).query.issue;
    if (raw === undefined) {
      set(deepLinkError, undefined);
      set(deepLinkIssueId, undefined);
      return;
    }

    const id = typeof raw === 'string' ? Number(raw) : Number.NaN;
    if (!Number.isInteger(id) || id <= 0) {
      set(deepLinkError, t('data_issues.deep_link.invalid', { id: String(raw) }));
      return;
    }

    if (id === get(deepLinkIssueId))
      return;

    set(deepLinkIssueId, id);
    set(deepLinkError, undefined);

    const result = await options.fetchIssue(id);
    if (id !== get(deepLinkIssueId))
      return;

    if (result.issue) {
      options.openDetail(result.issue);
      return;
    }

    set(deepLinkError, t('data_issues.deep_link.missing', {
      error: result.error ?? '',
      id,
    }));
  }

  watch(() => get(currentRoute).query.issue, () => {
    startPromise(openIssueFromQuery());
  }, { immediate: true });

  watch(options.drawerOpen, (open) => {
    if (!open)
      startPromise(clearIssueQuery());
  });

  return {
    clearIssueQuery,
    deepLinkError: readonly(deepLinkError),
  };
}
