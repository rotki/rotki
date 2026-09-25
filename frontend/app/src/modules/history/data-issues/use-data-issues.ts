import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import { pipe } from 'plainfp';
import { mapError, type ResultAsync } from 'plainfp/result-async';
import { type RequestError, toRequestError } from '@/modules/core/api/request-result';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';

interface UseDataIssuesReturn {
  fetchData: (payload: MaybeRef<DataIssuesRequestPayload>) => ResultAsync<Collection<DataIssue>, RequestError>;
  dismiss: (id: number) => Promise<DataIssue | undefined>;
  resolveManually: (id: number, note?: string) => Promise<DataIssue | undefined>;
  retry: (id: number) => Promise<DataIssue | undefined>;
}

export function useDataIssues(): UseDataIssuesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { dismissIssue, listIssues, resolveIssueManually, retryAutoRemediation } = useDataIssuesApi();
  const { setMessage } = useMessageStore();

  const fetchData = async (
    payload: MaybeRef<DataIssuesRequestPayload>,
  ): ResultAsync<Collection<DataIssue>, RequestError> => pipe(
    listIssues(get(payload)),
    mapError((error): RequestError => toRequestError(error.cause)),
  );

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
