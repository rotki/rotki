import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import { defaultCollectionState } from '@/modules/core/common/data/collection-utils';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';

interface UseDataIssuesReturn {
  fetchData: (payload: MaybeRef<DataIssuesRequestPayload>) => Promise<Collection<DataIssue>>;
  dismiss: (id: number) => Promise<DataIssue | undefined>;
  resolveManually: (id: number, note?: string) => Promise<DataIssue | undefined>;
  retry: (id: number) => Promise<DataIssue | undefined>;
}

export function useDataIssues(): UseDataIssuesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { dismissIssue, listIssues, resolveIssueManually, retryAutoRemediation } = useDataIssuesApi();
  const { notifyError } = useNotifications();
  const { setMessage } = useMessageStore();

  const fetchData = async (
    payload: MaybeRef<DataIssuesRequestPayload>,
  ): Promise<Collection<DataIssue>> => {
    const result = await listIssues(get(payload));
    if (result.ok)
      return result.value;

    notifyError(
      t('data_issues.fetch.error.title'),
      t('data_issues.fetch.error.message', { message: result.error.message }),
    );
    return defaultCollectionState<DataIssue>();
  };

  async function runAction(
    action: Promise<{ ok: true; value: DataIssue } | { ok: false; error: { message: string } }>,
    errorTitle: string,
  ): Promise<DataIssue | undefined> {
    const result = await action;
    if (result.ok)
      return result.value;

    setMessage({
      description: result.error.message,
      success: false,
      title: errorTitle,
    });
    return undefined;
  }

  const dismiss = async (id: number): Promise<DataIssue | undefined> =>
    runAction(dismissIssue(id), t('data_issues.action.dismiss.error'));

  const resolveManually = async (id: number, note?: string): Promise<DataIssue | undefined> =>
    runAction(resolveIssueManually(id, note), t('data_issues.action.resolve.error'));

  const retry = async (id: number): Promise<DataIssue | undefined> =>
    runAction(retryAutoRemediation(id), t('data_issues.action.retry.error'));

  return {
    dismiss,
    fetchData,
    resolveManually,
    retry,
  };
}
