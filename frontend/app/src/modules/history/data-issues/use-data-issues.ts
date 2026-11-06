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
  /** The actions report nothing themselves: the surface that ran one names its failure. */
  dismiss: (id: number) => ResultAsync<DataIssue, DataIssueError>;
  resolveManually: (id: number, note?: string) => ResultAsync<DataIssue, DataIssueError>;
  retry: (id: number) => ResultAsync<DataIssue, DataIssueError>;
}

export function useDataIssues(): UseDataIssuesReturn {
  const { dismissIssue, listIssues, resolveIssueManually, retryAutoRemediation } = useDataIssuesApi();

  const fetchData = async (
    payload: MaybeRef<DataIssuesRequestPayload>,
  ): ResultAsync<Collection<DataIssue>, RequestError> => pipe(
    listIssues(get(payload)),
    mapError((error): RequestError => toRequestError(error.cause)),
  );

  return {
    dismiss: dismissIssue,
    fetchData,
    resolveManually: resolveIssueManually,
    retry: retryAutoRemediation,
  };
}
