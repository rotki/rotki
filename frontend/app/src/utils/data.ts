import { BigNumber } from '@rotki/common';
import { isString, isUndefined } from 'es-toolkit';

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
 * Takes an object and returns the same object without any null values
 * or empty array properties.
 * @param object - Any object to process
 * @param options - Configuration options
 * @param options.removeEmptyString - If true, empty string properties will be removed
 * @param options.alwaysPickKeys - Array of keys that will always be included in the returned value
 * @returns A new object with non-empty properties
 */
export function nonEmptyProperties<T extends object>(
  object: T,
  { alwaysPickKeys = [], removeEmptyString = false }: {
    removeEmptyString?: boolean;
    alwaysPickKeys?: (keyof T)[];
  } = {},
): Partial<NonNullable<T>> {
  const partial: Partial<T> = {};
  const keys = Object.keys(object);
  if (object instanceof BigNumber)
    return object;

  for (const obKey of keys) {
    const key = obKey as keyof T;
    const val = object[key];

    if (alwaysPickKeys.includes(key)) {
      partial[key] = val;
    }

    if (removeEmptyString && val === '')
      continue;

    if (val === null)
      continue;

    if (Array.isArray(val)) {
      // TODO: monitor releases for a fix and restore when fix is released.
      // This is needed due to a bug in ts 5.1 where isArray doesn't narrow properly.
      const valArr = val as any[];
      if (valArr.length === 0)
        continue;

      partial[key] = valArr.map((v) => {
        if (typeof v === 'object')
          return nonEmptyProperties(v);

        return v;
      }) as T[keyof T];
    }
    else if (typeof val === 'object') {
      partial[key] = nonEmptyProperties(val) as T[keyof T];
    }
    else {
      partial[key] = val;
    }
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
