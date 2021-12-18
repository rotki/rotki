import { EntryMeta, EntryWithMeta } from '@/services/history/types';
import { Collection } from '@/types/collection';

export function mapCollectionEntriesWithMeta<T>(
  collection: Collection<EntryWithMeta<T>>
): Collection<T & EntryMeta> {
  const entries = collection.data.map(data => {
    const { entry, ...entriesMeta } = data;

    return {
      ...entry,
      ...entriesMeta
    };
  });
  return {
    ...collection,
    data: entries
  };
}
