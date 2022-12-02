import { Status } from '@/types/status';

/**
 * Returns true if a section is loading
 *
 * @deprecated use useStatusUpdater#loading instead
 * @param status
 */
export function isLoading(status: Status): boolean {
  return (
    status === Status.LOADING ||
    status === Status.PARTIALLY_LOADED ||
    status === Status.REFRESHING
  );
}

export type AddressEntries<T> = Readonly<Record<string, T>>;

export function filterAddresses<T>(
  entries: AddressEntries<T>,
  addresses: string[],
  item: (item: T) => void
): void {
  for (const address in entries) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }
    item(entries[address]);
  }
}
