import type { Collection } from '@/types/collection';
import type { EvmChainAndTxHash } from '@/types/history/events';
import type { EntryMeta, EntryWithMeta } from '@/types/history/meta';
import { uniqueStrings } from '@/utils/data';
import { snakeCase } from 'es-toolkit';

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

export function toEvmChainAndTxHash({ location, txHash }: { location: string; txHash?: string }): EvmChainAndTxHash {
  return {
    evmChain: snakeCase(location),
    txHash: txHash || '',
  };
}
