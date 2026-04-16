import type { IDType, InsertType, Table } from 'dexie';

export type ItemFilter<T> = (item: T) => boolean;

interface DataSet<T> {
  data: T[];
  total: number;
}

interface IndexedPagination<T> {
  orderBy: keyof T extends string ? keyof T : never;
  order: 'asc' | 'desc';
  offset: number;
  limit: number;
}

export async function getPage<T, ID extends keyof T>(
  table: Table<T, IDType<T, ID>, InsertType<T, ID>>,
  pagination: IndexedPagination<T>,
  filter?: ItemFilter<T>,
): Promise<DataSet<T>> {
  let collection = table.orderBy(`[${pagination.orderBy}]`);
  if (pagination.order === 'desc') {
    collection = collection.reverse();
  }

  const filteredCollection = (filter ? collection.filter(filter) : collection);
  const total = filter ? await filteredCollection.count() : await table.count();

  return {
    data: await filteredCollection.offset(pagination.offset).limit(pagination.limit).toArray(),
    total,
  };
}
