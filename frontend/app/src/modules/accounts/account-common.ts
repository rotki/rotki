import { camelCase } from 'es-toolkit';
import { objectKeys } from '@/modules/core/common/data/array';

const sortOptions: Intl.CollatorOptions = { sensitivity: 'accent', usage: 'sort' };

export function sortBy(a: any, b: any, asc: boolean): number {
  const [aValue, bValue] = asc ? [a, b] : [b, a];

  if (!isNaN(aValue) && !isNaN(bValue))
    return Number(aValue) - Number(bValue);

  return `${aValue}`.localeCompare(
    `${bValue}`,
    undefined,
    sortOptions,
  );
}

export function isFilterEnabled(filter?: string[] | string): boolean {
  return Array.isArray(filter) ? filter.length > 0 : !!filter;
}

export function includes(value: string, search: string): boolean {
  return value.toLocaleLowerCase().includes(search.toLocaleLowerCase());
}

/**
 * Finds the row property a table sort attribute names.
 *
 * @remarks
 * The table sends its sort keys in the backend's snake_case, while rows are camelCase, so the two
 * only meet after a conversion. An attribute the row has no property for yields `undefined`, and
 * the caller moves on to the next sort key rather than comparing nothing.
 *
 * @param row - the row to look the attribute up on
 * @param attribute - the sort attribute as the table sent it, in snake_case
 * @returns the matching key of `row`, or `undefined` when it has none
 */
export function sortKeyOf<T extends object>(row: T, attribute: string): keyof T | undefined {
  const converted = camelCase(attribute);
  return objectKeys(row).find(candidate => candidate === converted);
}

/**
 * Compares two rows by each table sort attribute in turn, so a tie on one falls through to the next.
 *
 * @remarks
 * `attributes` are the sort attributes as the table sent them, in snake_case, and `ascending` holds
 * the direction of each by position. An attribute the rows have no property for is skipped, as
 * {@link sortKeyOf} describes.
 */
export function compareByAttributes<T extends object>(a: T, b: T, attributes: string[], ascending: boolean[]): number {
  for (const [i, attribute] of attributes.entries()) {
    const key = sortKeyOf(a, attribute);
    if (!key)
      continue;

    const order = sortBy(a[key], b[key], ascending[i]);
    if (order)
      return order;
  }
  return 0;
}
