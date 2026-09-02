import { FetchError } from 'ofetch';
import { camelCaseTransformer, noRootCamelCaseTransformer } from '@/modules/core/api/transformers';
import { HTTPStatus } from '@/modules/core/api/types/http';

export interface ResponseParserOptions {
  skipCamelCase?: boolean;
  skipRootCamelCase?: boolean;
  /**
   * Fields whose nested object is left exactly as the backend sent it, for a value that is a map
   * rather than a record of fields. The field's own key is still camelCased.
   */
  camelCaseSkipKeys?: string[];
}

/**
 * Creates a response parser function based on transformation options.
 *
 * Falls back to `null` when the body is not valid JSON (e.g. an HTML 413
 * page from a reverse proxy) so the caller still reaches the status check
 * instead of crashing on a SyntaxError.
 */
export function createResponseParser(
  options: ResponseParserOptions,
): (text: string) => unknown {
  if (options.skipCamelCase)
    return (text: string): unknown => tryParseJson(text);
  if (options.skipRootCamelCase) {
    return (text: string): unknown => {
      const json = tryParseJson(text);
      return json === null ? null : noRootCamelCaseTransformer(json, options.camelCaseSkipKeys);
    };
  }
  return (text: string): unknown => {
    const json = tryParseJson(text);
    return json === null ? null : camelCaseTransformer(json, options.camelCaseSkipKeys);
  };
}

/**
 * Creates and throws a FetchError with status information.
 */
export function createStatusError(status: number, message?: string, data?: unknown): FetchError {
  const error = new FetchError(message ?? defaultMessageForStatus(status));
  error.status = status;
  error.statusCode = status;
  error.data = data;
  return error;
}

/**
 * True when the error is the backend saying the session is gone.
 *
 * @remarks
 * The sibling of {@link isRequestCancellation}: both mark an outcome the user should not be told
 * about, `handleAuthFailure` having already torn the session down.
 */
export function isSessionExpired(error: unknown): boolean {
  return error instanceof FetchError && error.status === HTTPStatus.UNAUTHORIZED;
}

function defaultMessageForStatus(status: number): string {
  if (status === 413)
    return 'The request body exceeds the limit configured on the server (likely a reverse proxy in front of rotki). Increase its upload size limit or use a smaller file.';
  if (status === 502 || status === 503 || status === 504)
    return 'The rotki backend is unreachable. It may be starting up, restarting, or overloaded — try again in a moment.';
  return `Request failed with status ${status}`;
}

/**
 * Safely parses JSON text, returning null on parse failure.
 */
export function tryParseJson<T>(text: string): T | null {
  try {
    return JSON.parse(text);
  }
  catch {
    return null;
  }
}
