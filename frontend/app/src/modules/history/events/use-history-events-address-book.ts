import type { AddressBookSimplePayload } from '@/modules/accounts/address-book/eth-names';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventCollectionRow } from '@/modules/history/events/schemas';
import { startPromise } from '@shared/utils';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getEthAddressesFromText } from '@/modules/history/history-utils';

interface UseHistoryEventsAddressBookReturn {
  populateAddressBook: (collection: Collection<HistoryEventCollectionRow>) => void;
}

export function useHistoryEventsAddressBook(): UseHistoryEventsAddressBookReturn {
  const { fetchEnsNames } = useEnsOperations();

  const { getChain } = useSupportedChains();

  function extractAddresses(
    notes: string | undefined,
    addressesNamesPayload: AddressBookSimplePayload[],
    location: string,
  ): void {
    if (!notes) {
      return;
    }
    addressesNamesPayload.push(
      ...getEthAddressesFromText(notes).map(address => ({
        address,
        blockchain: getChain(location),
      })),
    );
  }

  function populateAddressBook(collection: Collection<HistoryEventCollectionRow>): void {
    const addressesNamesPayload: AddressBookSimplePayload[] = [];

    for (const row of collection.data) {
      const events = arrayify(row);
      for (const { entry } of events) {
        extractAddresses(entry.userNotes, addressesNamesPayload, entry.location);
        extractAddresses(entry.autoNotes, addressesNamesPayload, entry.location);

        if ('address' in entry && entry.address) {
          extractAddresses(entry.address, addressesNamesPayload, entry.location);
        }
      }
    }

    if (addressesNamesPayload.length > 0)
      startPromise(fetchEnsNames(addressesNamesPayload));
  }

  return {
    populateAddressBook,
  };
}
