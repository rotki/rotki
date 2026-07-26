import { BigNumber } from '@rotki/common';
import { isString, isUndefined } from 'es-toolkit';
import { objectKeys } from '@/modules/core/common/data/array';

export function chunkArray<T>(myArray: T[], size: number): T[][] {
  const results: T[][] = [];

  while (myArray.length > 0) results.push(myArray.splice(0, size));

  return results;
}

export function uniqueStrings<T = string>(value: T, index: number, array: T[]): boolean {
  return array.indexOf(value) === index;
}

export function uniqueObjects<T>(arr: T[], getUniqueId: (item: T) => string): T[] {
  return [...new Map(arr.map(item => [getUniqueId(item), item])).values()];
}

/**
 * Returns `value` unless it is nullish or an empty string, in which case `fallback` is returned.
 * Preserves the `value || fallback` semantics (an empty string falls through) without a `||`.
 */
export function nonEmptyOr<T>(value: string | undefined | null, fallback: T): string | T {
  return value !== undefined && value !== null && value !== '' ? value : fallback;
}

/**
 * Takes an object and returns the same object without any null values
 * or empty array properties.
 * @param object - Any object to process
 * @param options - Configuration options
 * @param options.removeEmptyString - If true, empty string properties will be removed
 * @param options.alwaysPickKeys - Array of keys that will always be included in the returned value
 * @returns A new object with non-empty properties
 */
interface NonEmptyPropertiesOptions<T> {
  removeEmptyString?: boolean;
  alwaysPickKeys?: (keyof T)[];
}

/**
 * Resolving the defaults here rather than in the parameter list keeps them out of the caller's
 * complexity budget, which counts every defaulted field as a branch.
 */
function withNonEmptyDefaults<T>(options: NonEmptyPropertiesOptions<T>): Required<NonEmptyPropertiesOptions<T>> {
  return {
    alwaysPickKeys: options.alwaysPickKeys ?? [],
    removeEmptyString: options.removeEmptyString ?? false,
  };
}

/** An empty array carries no information, and null is dropped whatever the options say. */
function isEmptyValue(val: unknown, removeEmptyString: boolean): boolean {
  if (val === null)
    return true;

  if (removeEmptyString && val === '')
    return true;

  return Array.isArray(val) && val.length === 0;
}

/**
 * Nested objects are pruned too, including those inside arrays.
 *
 * The result is a deep partial of what came in, so it cannot be typed as the input type. Declaring
 * it as one was tried and needs a recursive conditional with its own array branch, which changes the
 * public return type of nonEmptyProperties and every caller that feeds it a request body. The
 * assertion is therefore left at the single assignment below rather than spread over this helper.
 */
function pruneValue(val: unknown): unknown {
  if (Array.isArray(val))
    return val.map(entry => isPrunable(entry) ? nonEmptyProperties(entry) : entry);

  if (isPrunable(val))
    return nonEmptyProperties(val);

  return val;
}

function isPrunable(value: unknown): value is object {
  return typeof value === 'object' && value !== null;
}

export function nonEmptyProperties<T extends object>(
  object: T,
  options: NonEmptyPropertiesOptions<T> = {},
): Partial<NonNullable<T>> {
  if (object instanceof BigNumber)
    return object;

  const { alwaysPickKeys, removeEmptyString } = withNonEmptyDefaults(options);
  const partial: Partial<T> = {};

  for (const key of objectKeys(object)) {
    const val = object[key];

    // An always-picked key is written first and then still pruned below, as it was before.
    if (alwaysPickKeys.includes(key))
      partial[key] = val;

    if (isEmptyValue(val, removeEmptyString))
      continue;

    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- see pruneValue
    partial[key] = pruneValue(val) as T[keyof T];
  }

  return partial;
}

export function size(bytes: number): string {
  let i = 0;

  for (i; bytes > 1024; i++) bytes /= 1024;

  const symbol = 'KMGTPEZY'[i - 1] || '';
  return `${bytes.toFixed(2)}  ${symbol}B`;
}

/**
 * Converts a string or number to rems
 * @param {number | string} value
 * @returns {string} - the converted value in rems
 */
export function toRem(value?: number | string): string | undefined {
  if (isUndefined(value) || value === 'auto')
    return value;

  if (isString(value)) {
    if (value.endsWith('rem') || value.endsWith('%'))
      return value;

    if (value.endsWith('px'))
      return `${Number(value.replace('px', '')) / 16}rem`;
  }

  return `${value}rem`;
}

/**
 * Returns a copy of the record without the key in it.
 * @param record The record
 * @param key The key to remove
 */
export function removeKey<K extends string | number | symbol, V>(record: Record<K, V>, key: K): Record<K, V> {
  const copy = { ...record };
  delete copy[key];
  return copy;
}
