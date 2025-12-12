import { FetchError } from 'ofetch';
import { camelCaseTransformer, noRootCamelCaseTransformer } from '@/modules/api/transformers';

export interface ResponseParserOptions {
  skipCamelCase?: boolean;
  skipRootCamelCase?: boolean;
}

/**
 * Creates a response parser function based on transformation options.
 */
export function createResponseParser(
  options: ResponseParserOptions,
): (text: string) => unknown {
  if (options.skipCamelCase)
    return (text: string) => JSON.parse(text);
  if (options.skipRootCamelCase)
    return (text: string) => noRootCamelCaseTransformer(JSON.parse(text));
  return (text: string) => camelCaseTransformer(JSON.parse(text));
}

/**
 * Creates and throws a FetchError with status information.
 */
export function createStatusError(status: number, message?: string, data?: unknown): FetchError {
  const error = new FetchError(message || `Request failed with status ${status}`);
  error.status = status;
  error.statusCode = status;
  error.data = data;
  return error;
}

/**
 * Safely parses JSON text, returning null on parse failure.
 */
export function tryParseJson<T>(text: string): T | null {
  try {
    return JSON.parse(text) as T;
  }
  catch {
    return null;
  }
}
