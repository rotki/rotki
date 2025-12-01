import { BigNumber, isEvmIdentifier, transformCase } from '@rotki/common';

function isObject(data: unknown): data is Record<string, unknown> {
  return (
    typeof data === 'object'
    && data !== null
    && !(data instanceof RegExp)
    && !(data instanceof Error)
    && !(data instanceof Date)
    && !(data instanceof BigNumber)
  );
}

function getUpdatedKey(key: string, camelCase: boolean): string {
  return transformCase(key, camelCase);
}

function convertKeys(data: unknown, camelCase: boolean, skipKey: boolean): unknown {
  if (Array.isArray(data))
    return data.map(entry => convertKeys(entry, camelCase, false));

  if (!isObject(data))
    return data;

  const converted: Record<string, unknown> = {};
  Object.keys(data).forEach((key) => {
    const datum = data[key];
    const skipConversion = skipKey || isEvmIdentifier(key) || /^[A-Z]/.test(key);
    const updatedKey = skipConversion ? key : getUpdatedKey(key, camelCase);

    converted[updatedKey] = isObject(datum) ? convertKeys(datum, camelCase, skipKey && key === 'result') : datum;
    return key;
  });

  return converted;
}

export function snakeCaseTransformer<T>(data: T): T {
  return convertKeys(data, false, false) as T;
}

export function camelCaseTransformer<T>(data: T): T {
  return convertKeys(data, true, false) as T;
}

export function noRootCamelCaseTransformer<T>(data: T): T {
  return convertKeys(data, true, true) as T;
}

/**
 * Transforms query parameters for URL serialization:
 * - Converts keys to snake_case
 * - Joins arrays with commas (e.g., ['USD', 'EUR'] -> 'USD,EUR')
 * - Removes null/undefined values
 */
export function queryTransformer(data: Record<string, unknown>): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};

  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined)
      continue;

    const snakeKey = transformCase(key, false);

    if (Array.isArray(value)) {
      result[snakeKey] = value.join(',');
    }
    else if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      result[snakeKey] = value;
    }
    else if (typeof value === 'object') {
      // For nested objects, stringify them
      result[snakeKey] = JSON.stringify(snakeCaseTransformer(value));
    }
  }

  return result;
}
