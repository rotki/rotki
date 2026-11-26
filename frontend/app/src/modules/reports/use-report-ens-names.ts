import type { AddressBookSimplePayload } from '@/modules/accounts/address-book/eth-names';
import type { Collection } from '@/modules/core/common/collection';
import type { ProfitLossEvent } from '@/modules/reports/report-types';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { isBlockchain } from '@/modules/core/common/chains';
import { getEthAddressesFromText } from '@/modules/history/history-utils';
import { isTransactionEvent } from '@/modules/reports/report-utils';

interface UseReportEnsNamesReturn {
  fetchEnsNamesFromTransactions: (events: Collection<ProfitLossEvent>) => void;
}

/** Looks up ENS names for the addresses mentioned in the notes of a report's transaction events. */
export function useReportEnsNames(): UseReportEnsNamesReturn {
  const { fetchEnsNames } = useEnsOperations();

  function fetchEnsNamesFromTransactions(events: Collection<ProfitLossEvent>): void {
    const addressesNamesPayload: AddressBookSimplePayload[] = [];
    events.data
      .filter(event => isTransactionEvent(event))
      .forEach((event) => {
        const blockchain = event.location || Blockchain.ETH;
        if (!event.notes || !isBlockchain(blockchain))
          return;

        const addresses = getEthAddressesFromText(event.notes);
        addressesNamesPayload.push(
          ...addresses.map(address => ({
            address,
            blockchain,
          })),
        );
      });

    if (addressesNamesPayload.length > 0)
      startPromise(fetchEnsNames(addressesNamesPayload));
  }

  return {
    fetchEnsNamesFromTransactions,
  };
}
