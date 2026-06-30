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

// Keep 200 and 400 as "valid" statuses so a 400 still unwraps through the shared
// wrapper into an ApiValidationError that carries the backend's structured
// validation payload. 409 is deliberately excluded so it surfaces as a FetchError
// with `status` (the wrapper would otherwise swallow it into a plain, status-less
// Error), letting toDataIssueError tell a conflict apart from a network failure.
const VALID_STATUSES = { validStatuses: [HTTPStatus.OK, HTTPStatus.BAD_REQUEST] } as const;

/**
 * Classifies a thrown API error into the typed {@link DataIssueError} domain.
 *
 * With {@link VALID_STATUSES}, a 400 arrives as an {@link ApiValidationError}
 * (wrapping the backend validation data) and every other rejected status as a
 * {@link FetchError} with `status`: 404 -> not-found, 409 (invalid state
 * transition) -> conflict, 400 -> validation, anything else -> network.
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
