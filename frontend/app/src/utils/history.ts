import { type EntryMeta, type EntryWithMeta } from '@/types/history/meta';
import { type EvmChainAndTxHash } from '@/types/history/events';
import { type Collection } from '@/types/collection';

export function mapCollectionEntriesWithMeta<T>(
  collection: Collection<EntryWithMeta<T>>
): Collection<T & EntryMeta> {
  const entries = collection.data.map(data => transformEntryWithMeta<T>(data));
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

export const getEthAddressesFromText = (notes: string[]): string[] =>
  filterAddressesFromWords(notes.join(' ').split(/\s|\\n/));

export const toEvmChainAndTxHash = ({
  location,
  eventIdentifier
}: {
  location: string;
  eventIdentifier: string;
}): EvmChainAndTxHash => ({
  evmChain: location,
  txHash: eventIdentifier
});
