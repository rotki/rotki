import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import type { DataIssueError } from '@/modules/history/data-issues/types';
import { pipe } from 'plainfp';
import { mapError, type ResultAsync } from 'plainfp/result-async';
import { type RequestError, toRequestError } from '@/modules/core/api/request-result';
import { useDataIssuesApi } from '@/modules/history/data-issues/api/use-data-issues-api';

interface UseDataIssuesReturn {
  fetchData: (payload: MaybeRef<DataIssuesRequestPayload>) => ResultAsync<Collection<DataIssue>, RequestError>;
  fetchIssue: (id: number) => Promise<{ issue?: DataIssue; error?: string }>;
  /** The actions report nothing themselves: the surface that ran one names its failure. */
  dismiss: (id: number) => ResultAsync<DataIssue, DataIssueError>;
  resolveManually: (id: number, note?: string) => ResultAsync<DataIssue, DataIssueError>;
  retry: (id: number) => ResultAsync<DataIssue, DataIssueError>;
}

export function useDataIssues(): UseDataIssuesReturn {
  const { dismissIssue, getIssue, listIssues, resolveIssueManually, retryAutoRemediation } = useDataIssuesApi();

  const fetchData = async (
    payload: MaybeRef<DataIssuesRequestPayload>,
  ): ResultAsync<Collection<DataIssue>, RequestError> => pipe(
    listIssues(get(payload)),
    mapError((error): RequestError => toRequestError(error.cause)),
  );

  /**
   * Reads one issue independently of the list filters, returning dead-link errors inline.
   */
  const fetchIssue = async (id: number): Promise<{ issue?: DataIssue; error?: string }> => {
    const result = await getIssue(id);
    if (result.ok)
      return { issue: result.value };

    return { error: result.error.message };
  };

  return {
    dismiss: dismissIssue,
    fetchData,
    fetchIssue,
    resolveManually: resolveIssueManually,
    retry: retryAutoRemediation,
  };
}
