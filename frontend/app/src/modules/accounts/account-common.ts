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
