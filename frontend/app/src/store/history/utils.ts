import { EntryMeta, EntryWithMeta } from '@/services/history/types';
import { Collection } from '@/types/collection';
import { uniqueStrings } from '@/utils/data';

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

export function filterAddressesFromWords(words: string[]): string[] {
  return words
    .filter((word, index) => {
      // Check if the word is ETH address
      const isAddress = word.startsWith('0x') && word.length >= 42;

      // Check if the word is Tx Hash
      const isTransaction =
        isAddress && index !== 0 && words[index - 1] === 'transaction';

      return isAddress && !isTransaction;
    })
    .filter(uniqueStrings);
}
