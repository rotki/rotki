import type { NonEmptyPropertiesOptions } from '@/modules/api/types';
import { queryTransformer, snakeCaseTransformer } from '@/modules/api/transformers';
import { nonEmptyProperties } from '@/utils/data';

export interface TransformOptions {
  skipSnakeCase?: boolean;
  filterEmptyProperties?: true | NonEmptyPropertiesOptions;
}

/**
 * Transforms request body: filters empty properties and converts to snake_case.
 */
export function transformRequestBody(
  body: BodyInit | Record<string, unknown> | null | undefined,
  options: TransformOptions,
): BodyInit | Record<string, unknown> | null | undefined {
  if (!body || body instanceof FormData)
    return body;

  let transformed = body as Record<string, unknown>;

  if (options.filterEmptyProperties) {
    const filterOptions = options.filterEmptyProperties === true ? {} : options.filterEmptyProperties;
    transformed = nonEmptyProperties(transformed, filterOptions);
  }

  if (!options.skipSnakeCase)
    transformed = snakeCaseTransformer(transformed);

  return transformed;
}

/**
 * Transforms query parameters: filters empty properties and converts to snake_case.
 */
export function transformRequestQuery(
  query: Record<string, unknown> | undefined,
  options: TransformOptions,
): Record<string, string | number | boolean> | undefined {
  if (!query)
    return undefined;

  let transformed = query;

  if (options.filterEmptyProperties) {
    const filterOptions = options.filterEmptyProperties === true ? {} : options.filterEmptyProperties;
    transformed = nonEmptyProperties(transformed, filterOptions);
  }

  if (!options.skipSnakeCase)
    return queryTransformer(transformed);

  return transformed as Record<string, string | number | boolean>;
}
