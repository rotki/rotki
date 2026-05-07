import { FetchError } from 'ofetch';
import { camelCaseTransformer, noRootCamelCaseTransformer } from '@/modules/core/api/transformers';

export interface ResponseParserOptions {
  skipCamelCase?: boolean;
  skipRootCamelCase?: boolean;
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
      return json === null ? null : noRootCamelCaseTransformer(json);
    };
  }
  return (text: string): unknown => {
    const json = tryParseJson(text);
    return json === null ? null : camelCaseTransformer(json);
  };
}

/**
 * Creates and throws a FetchError with status information.
 */
export function createStatusError(status: number, message?: string, data?: unknown): FetchError {
  const error = new FetchError(message || defaultMessageForStatus(status));
  error.status = status;
  error.statusCode = status;
  error.data = data;
  return error;
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
