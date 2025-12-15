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

interface ConvertKeysOptions {
  camelCase: boolean;
  /** Keys whose nested values should NOT be recursively converted */
  skipKeys?: string[];
  /** Skip key conversion at root level only (propagates only to 'result' key) */
  skipRoot?: boolean;
}

function convertKeys(data: unknown, options: ConvertKeysOptions): unknown {
  const { camelCase, skipKeys = [], skipRoot = false } = options;

  if (Array.isArray(data))
    return data.map(entry => convertKeys(entry, { camelCase, skipKeys, skipRoot: false }));

  if (!isObject(data))
    return data;

  const converted: Record<string, unknown> = {};
  Object.keys(data).forEach((key) => {
    const datum = data[key];
    const skipConversion = skipRoot || isEvmIdentifier(key) || /^[A-Z]/.test(key);
    const updatedKey = skipConversion ? key : getUpdatedKey(key, camelCase);
    const shouldSkipNested = skipKeys.includes(key);

    converted[updatedKey] = isObject(datum) && !shouldSkipNested
      ? convertKeys(datum, { camelCase, skipKeys, skipRoot: skipRoot && key === 'result' })
      : datum;
    return key;
  });

  return converted;
}

export function snakeCaseTransformer<T>(data: T, skipKeys?: string[]): T {
  return convertKeys(data, { camelCase: false, skipKeys }) as T;
}

export function camelCaseTransformer<T>(data: T): T {
  return convertKeys(data, { camelCase: true }) as T;
}

export function noRootCamelCaseTransformer<T>(data: T): T {
  return convertKeys(data, { camelCase: true, skipRoot: true }) as T;
}

/**
 * Transforms query parameters for URL serialization:
 * - Converts keys to snake_case
 * - Joins arrays with commas (e.g., ['USD', 'EUR'] -> 'USD,EUR')
 * - Removes null/undefined values
 */
export function queryTransformer(data: Record<string, unknown>, skipKeys?: string[]): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};

  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined)
      continue;

    const snakeKey = transformCase(key, false);
    const shouldSkipNested = skipKeys?.includes(key) ?? false;

    if (Array.isArray(value)) {
      result[snakeKey] = value.join(',');
    }
    else if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      result[snakeKey] = value;
    }
    else if (typeof value === 'object') {
      // For nested objects, stringify them
      result[snakeKey] = shouldSkipNested ? JSON.stringify(value) : JSON.stringify(snakeCaseTransformer(value, skipKeys));
    }
  }

  return result;
}
