import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { Collection } from '@/types/collection';
import { HistoryRequestPayload } from '@/types/history';
import { EntryMeta, EntryWithMeta } from '@/types/history/meta';
import { uniqueStrings } from '@/utils/data';
import { isValidEthAddress } from '@/utils/text';

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
  return words.filter(uniqueStrings).filter(isValidEthAddress);
}

export const defaultHistoricPayloadState = <
  T extends Object
>(): HistoryRequestPayload<T> => {
  const store = useFrontendSettingsStore();

  return {
    limit: store.itemsPerPage,
    offset: 0,
    orderByAttributes: ['timestamp' as keyof T],
    ascending: [false]
  };
};
