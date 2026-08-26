import type { Collection } from '@/modules/core/common/collection';
import type { DataIssueError } from '@/modules/history/data-issues/types';
import { omit } from 'es-toolkit';
import { FetchError } from 'ofetch';
import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { api } from '@/modules/core/api/rotki-api';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { HTTPStatus } from '@/modules/core/api/types/http';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { type DataIssue, DataIssue as DataIssueSchema, DataIssuesCollectionResponse, type DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';

const BASE = '/data_issues';

const VALID_STATUSES = { validStatuses: [HTTPStatus.OK, HTTPStatus.BAD_REQUEST] } as const;

/**
 * Classifies a thrown API error into the typed {@link DataIssueError} domain.
 *
 * @remarks
 * With {@link VALID_STATUSES}, a `400` arrives as an {@link ApiValidationError} wrapping the backend
 * validation data, and every other rejected status as a {@link FetchError} carrying `status`. Those
 * map as `404` to not-found, `409` to conflict (an invalid state transition), `400` to validation,
 * and anything else to network.
 *
 * @param cause - the value thrown by the failed request
 * @returns the typed error the UI branches on
 */
function toDataIssueError(cause: unknown): DataIssueError {
  const message = getErrorMessage(cause);
  if (cause instanceof FetchError && cause.status === 404)
    return { message, type: 'not-found' };
  if (cause instanceof FetchError && cause.status === 409)
    return { message, type: 'conflict' };
  // 400 validation errors arrive as ApiValidationError wrapping the backend's field data.
  if (cause instanceof ApiValidationError || (cause instanceof FetchError && cause.status === 400))
    return { message, type: 'validation' };
  return { message, type: 'network' };
}

interface UseDataIssuesApiReturn {
  listIssues: (payload: DataIssuesRequestPayload) => ResultAsync<Collection<DataIssue>, DataIssueError>;
  getIssue: (id: number) => ResultAsync<DataIssue, DataIssueError>;
  dismissIssue: (id: number) => ResultAsync<DataIssue, DataIssueError>;
  resolveIssueManually: (id: number, note?: string) => ResultAsync<DataIssue, DataIssueError>;
  retryAutoRemediation: (id: number) => ResultAsync<DataIssue, DataIssueError>;
}

export function useDataIssuesApi(): UseDataIssuesApiReturn {
  const listIssues = async (
    payload: DataIssuesRequestPayload,
  ): ResultAsync<Collection<DataIssue>, DataIssueError> =>
    fromAsync(async () => {
      // The `/data_issues` endpoint orders rows server-side (ts_start desc) and
      // its schema does not accept ordering params; strip the sort keys the shared
      // pagination composable injects so the backend doesn't reject the request.
      const query = omit(payload, ['orderByAttributes', 'ascending']);
      const response = await api.get<unknown>(BASE, {
        ...VALID_STATUSES,
        filterEmptyProperties: { removeEmptyString: true },
        query,
      });
      return mapCollectionResponse(DataIssuesCollectionResponse.parse(response));
    }, toDataIssueError);

  const getIssue = async (id: number): ResultAsync<DataIssue, DataIssueError> =>
    fromAsync(async () => {
      const response = await api.get<unknown>(`${BASE}/${id}`, VALID_STATUSES);
      return DataIssueSchema.parse(response);
    }, toDataIssueError);

  const dismissIssue = async (id: number): ResultAsync<DataIssue, DataIssueError> =>
    fromAsync(async () => {
      const response = await api.patch<unknown>(`${BASE}/${id}/dismiss`, null, VALID_STATUSES);
      return DataIssueSchema.parse(response);
    }, toDataIssueError);

  const resolveIssueManually = async (id: number, note?: string): ResultAsync<DataIssue, DataIssueError> =>
    fromAsync(async () => {
      const response = await api.patch<unknown>(`${BASE}/${id}/resolve_manually`, note ? { note } : null, VALID_STATUSES);
      return DataIssueSchema.parse(response);
    }, toDataIssueError);

  const retryAutoRemediation = async (id: number): ResultAsync<DataIssue, DataIssueError> =>
    fromAsync(async () => {
      const response = await api.post<unknown>(`${BASE}/${id}/retry_auto_remediation`, null, VALID_STATUSES);
      return DataIssueSchema.parse(response);
    }, toDataIssueError);

  return {
    dismissIssue,
    getIssue,
    listIssues,
    resolveIssueManually,
    retryAutoRemediation,
  };
}
