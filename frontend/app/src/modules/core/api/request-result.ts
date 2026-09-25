import { FetchError } from 'ofetch';
import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { hasTag, tag } from 'plainfp/tagged';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';

/**
 * The request was cancelled rather than failed: by `cancelByTag`, logout, a user switch or quit.
 * Expected, so a consumer drops it quietly instead of reporting it.
 */
export const RequestCancelled = tag('RequestCancelled');

/** The request reached a verdict and it was a failure. */
export const RequestFailed = tag('RequestFailed');

export type RequestFailure = ReturnType<typeof RequestFailed<{
  message: string;
  /** The HTTP status, when the failure came from a response rather than the client. */
  status?: number;
  /** The url that failed, when known. */
  path?: string;
  /** The value the request threw, kept for callers that branch on its class. */
  cause: unknown;
}>>;

export type RequestError =
  | ReturnType<typeof RequestCancelled<{ message: string }>>
  | RequestFailure;

/** True when the error is a real failure rather than a cancellation. */
export function isRequestFailure(error: RequestError): error is RequestFailure {
  return hasTag(error, 'RequestFailed');
}

/** The message the backend put in the response body, which reads better than the error's own. */
function responseMessage(data: unknown): string | undefined {
  if (typeof data !== 'object' || data === null || !('message' in data))
    return undefined;

  return typeof data.message === 'string' ? data.message : undefined;
}

/**
 * Classifies the value a failed request threw into a {@link RequestError}.
 *
 * @remarks
 * Exported for domain errors that keep the thrown value, so a table fetch built on one reports the
 * status and a cancellation the same way {@link fromRequest} does.
 */
export function toRequestError(cause: unknown): RequestError {
  if (isRequestCancellation(cause))
    return RequestCancelled({ message: getErrorMessage(cause) });

  const fetchError = cause instanceof FetchError ? cause : undefined;

  return RequestFailed({
    cause,
    message: responseMessage(fetchError?.data) ?? getErrorMessage(cause),
    path: fetchError?.request?.toString(),
    status: fetchError?.statusCode,
  });
}

/** Runs a request and carries its failure as a value instead of a rejection. */
export async function fromRequest<T>(request: () => Promise<T>): ResultAsync<T, RequestError> {
  return fromAsync(request, toRequestError);
}
