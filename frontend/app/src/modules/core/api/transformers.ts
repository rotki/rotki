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

/**
 * Renames every key in the payload, so the result is structurally a different type than the input.
 * Callers nevertheless treat it as the same shape, because the renamed shape is exactly what their
 * own type describes: the snake_case wire form on the way out, the camelCase model on the way in.
 *
 * Expressing that in the type system was attempted and rejected: a mapped type over CamelCase would
 * change the public signature of every transformer, and it would still be wrong, since conversion is
 * skipped for EVM identifiers and capitalised keys. The generic is therefore asserted once here
 * rather than at each of the three call sites below.
 */
function convertKeysRecursively(data: unknown, options: ConvertKeysOptions): unknown {
  const { camelCase, skipKeys = [], skipRoot = false } = options;

  if (Array.isArray(data))
    return data.map(entry => convertKeysRecursively(entry, { camelCase, skipKeys, skipRoot: false }));

  if (!isObject(data))
    return data;

  const converted: Record<string, unknown> = {};
  Object.keys(data).forEach((key) => {
    const datum = data[key];
    const skipConversion = skipRoot || isEvmIdentifier(key) || /^[A-Z]/.test(key);
    const updatedKey = skipConversion ? key : getUpdatedKey(key, camelCase);
    const shouldSkipNested = skipKeys.includes(key);

    converted[updatedKey] = isObject(datum) && !shouldSkipNested
      ? convertKeysRecursively(datum, { camelCase, skipKeys, skipRoot: skipRoot && key === 'result' })
      : datum;
    return key;
  });

  return converted;
}

function convertKeys<T>(data: T, options: ConvertKeysOptions): T {
  // The one assertion for the whole transformer family lives here rather than at each caller;
  // see the note on convertKeys above for what was tried instead.
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- see above
  return convertKeysRecursively(data, options) as T;
}

export function snakeCaseTransformer<T>(data: T, skipKeys?: string[]): T {
  return convertKeys(data, { camelCase: false, skipKeys });
}

export function camelCaseTransformer<T>(data: T): T {
  return convertKeys(data, { camelCase: true });
}

export function noRootCamelCaseTransformer<T>(data: T): T {
  return convertKeys(data, { camelCase: true, skipRoot: true });
}

/**
 * Transforms query parameters for URL serialization:
 * - Converts keys to snake_case
 * - Joins arrays with commas (e.g., ['USD', 'EUR'] -> 'USD,EUR')
 * - Removes null/undefined values
 */
/**
 * A query string carries scalars, so arrays are joined and objects stringified. Anything else has no
 * query representation and is reported as undefined so the caller drops the key.
 */
function toQueryValue(
  value: unknown,
  skipNested: boolean,
  skipKeys?: string[],
): string | number | boolean | undefined {
  if (Array.isArray(value))
    return value.join(',');

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')
    return value;

  if (typeof value === 'object')
    return skipNested ? JSON.stringify(value) : JSON.stringify(snakeCaseTransformer(value, skipKeys));

  return undefined;
}

export function queryTransformer(data: Record<string, unknown>, skipKeys?: string[]): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {};

  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined)
      continue;

    const queryValue = toQueryValue(value, skipKeys?.includes(key) ?? false, skipKeys);
    if (queryValue !== undefined)
      result[transformCase(key, false)] = queryValue;
  }

  return result;
}
