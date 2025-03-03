import type { IDType, InsertType, Table } from 'dexie';

export type ItemFilter<T> = (item: T) => boolean;

export interface IndexedPagination<T> {
  orderBy: keyof T extends string ? keyof T : never;
  order: 'asc' | 'desc';
  offset: number;
  limit: number;
}

export async function getPage<T, ID extends keyof T>(
  table: Table<T, IDType<T, ID>, InsertType<T, ID>>,
  idProp: ID,
  pagination: IndexedPagination<T>,
  filter?: ItemFilter<T>,
): Promise<T[]> {
  let collection = table.orderBy(`[${pagination.orderBy}]`);
  if (pagination.order === 'desc') {
    collection = collection.reverse();
  }

  return (filter ? collection.filter(filter) : collection).offset(pagination.offset).limit(pagination.limit).toArray();
}
