import type { NonEmptyPropertiesOptions } from '@/modules/core/api/types';
import { queryTransformer, snakeCaseTransformer } from '@/modules/core/api/transformers';
import { nonEmptyProperties } from '@/modules/core/common/data/data';

/**
 * BodyInit covers strings, blobs and streams as well as the plain objects the API is given. Only the
 * latter can have their keys renamed, so the others are recognised and passed through.
 */
function isPlainBody(
  body: BodyInit | Record<string, unknown> | null | undefined,
): body is Record<string, unknown> {
  return typeof body === 'object'
    && body !== null
    && !(body instanceof FormData)
    && !(body instanceof Blob)
    && !(body instanceof URLSearchParams)
    && !(body instanceof ReadableStream)
    && !(body instanceof ArrayBuffer)
    && !ArrayBuffer.isView(body);
}

export interface TransformOptions {
  skipSnakeCase?: boolean | string[];
  filterEmptyProperties?: true | NonEmptyPropertiesOptions;
}

/**
 * Transforms request body: filters empty properties and converts to snake_case.
 */
export function transformRequestBody(
  body: BodyInit | Record<string, unknown> | null | undefined,
  options: TransformOptions,
): BodyInit | Record<string, unknown> | null | undefined {
  // Only a plain payload object is transformed; every other BodyInit is sent through untouched.
  if (!isPlainBody(body))
    return body;

  let transformed = body;

  if (options.filterEmptyProperties) {
    const filterOptions = options.filterEmptyProperties === true ? {} : options.filterEmptyProperties;
    transformed = nonEmptyProperties(transformed, filterOptions);
  }

  if (options.skipSnakeCase !== true) {
    const skipKeys = Array.isArray(options.skipSnakeCase) ? options.skipSnakeCase : undefined;
    transformed = snakeCaseTransformer(transformed, skipKeys);
  }

  return transformed;
}

/**
 * Transforms query parameters: filters empty properties and converts to snake_case.
 */
export function transformRequestQuery(
  query: Record<string, unknown> | undefined,
  options: TransformOptions,
): Record<string, unknown> | undefined {
  if (!query)
    return undefined;

  let transformed = query;

  if (options.filterEmptyProperties) {
    const filterOptions = options.filterEmptyProperties === true ? {} : options.filterEmptyProperties;
    transformed = nonEmptyProperties(transformed, filterOptions);
  }

  if (options.skipSnakeCase !== true) {
    const skipKeys = Array.isArray(options.skipSnakeCase) ? options.skipSnakeCase : undefined;
    return queryTransformer(transformed, skipKeys);
  }

  // skipSnakeCase leaves both the keys and the values alone, so the bag is handed back as it is.
  return transformed;
}
