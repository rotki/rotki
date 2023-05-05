import { BigNumber } from '@rotki/common';

export function chunkArray<T>(myArray: T[], size: number): T[][] {
  const results: T[][] = [];

  while (myArray.length > 0) {
    results.push(myArray.splice(0, size));
  }

  return results;
}

export const uniqueStrings = <T = string>(
  value: T,
  index: number,
  array: T[]
): boolean => array.indexOf(value) === index;

export const uniqueObjects = <T>(
  arr: T[],
  getUniqueId: (item: T) => string
) => [...new Map(arr.map(item => [getUniqueId(item), item])).values()];

/**
 * Takes an object and returns the same object without any null values
 * or empty array properties.
 * @param object any object
 */
export const nonEmptyProperties = <T extends object>(
  object: T,
  removeEmptyString = false
): Partial<NonNullable<T>> => {
  const partial: Partial<T> = {};
  const keys = Object.keys(object);
  if (object instanceof BigNumber) {
    return object;
  }
  for (const obKey of keys) {
    const key = obKey as keyof T;
    const val = object[key];
    if (removeEmptyString && val === '') {
      continue;
    }
    if (val === null) {
      continue;
    }
    if (Array.isArray(val)) {
      if (val.length === 0) {
        continue;
      }
      partial[key] = val.map(v => {
        if (typeof v === 'object') {
          return nonEmptyProperties(v);
        }
        return v;
      }) as T[keyof T];
    } else if (typeof val === 'object') {
      partial[key] = nonEmptyProperties(val) as T[keyof T];
    } else {
      partial[key] = val;
    }
  }
  return partial;
};

export const size = (bytes: number): string => {
  let i = 0;

  for (i; bytes > 1024; i++) {
    bytes /= 1024;
  }

  const symbol = 'KMGTPEZY'[i - 1] || '';
  return `${bytes.toFixed(2)}  ${symbol}B`;
};
