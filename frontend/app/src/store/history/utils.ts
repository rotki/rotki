import { EntryMeta, EntryWithMeta } from '@/services/history/types';
import { Collection } from '@/types/collection';

export function mapCollectionEntriesWithMeta<T>(
  collection: Collection<EntryWithMeta<T>>
): Collection<T & EntryMeta> {
  const entries = collection.data.map(data => {
    return transformEntryWithMeta<T>(data);
  });
  return {
    ...collection,
    data: entries
  };
}

export function transformEntryWithMeta<T>(
  data: EntryWithMeta<T>
): T & EntryMeta {
  const { entry, ...entriesMeta } = data;

  return {
    ...entry,
    ...entriesMeta
  };
}
