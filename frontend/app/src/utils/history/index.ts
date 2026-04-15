import type { Collection } from '@/modules/common/collection';
import type { EntryMeta, EntryWithMeta } from '@/modules/history/meta';
import { isValidEthAddress } from '@rotki/common';
import { uniqueStrings } from '@/utils/data';

export function mapCollectionEntriesWithMeta<T>(collection: Collection<EntryWithMeta<T>>): Collection<T & EntryMeta> {
  const entries = collection.data.map(data => transformEntryWithMeta<T>(data));
  return {
    ...collection,
    data: entries,
  };
}

export function transformEntryWithMeta<T>(data: EntryWithMeta<T>): T & EntryMeta {
  const { entry, ...entriesMeta } = data;

  return {
    ...entry,
    ...entriesMeta,
  };
}

export function filterAddressesFromWords(words: string[]): string[] {
  return words.filter(uniqueStrings).filter(isValidEthAddress);
}

export function getEthAddressesFromText(notes: string): string[] {
  return filterAddressesFromWords(notes.split(/\s|\\n/));
}
