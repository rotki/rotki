import type { Ref } from 'vue';
import type { AddressInteraction } from './address-interaction-types';
import type { AddressBookSimplePayload } from '@/modules/accounts/address-book/eth-names';
import { startPromise } from '@shared/utils';
import { z } from 'zod';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { api } from '@/modules/core/api/rotki-api';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';

const AddressInteractions = z.array(z.object({
  chain: z.string(),
  source: z.string(),
  target: z.string(),
  txHash: z.string(),
}));

/**
 * The addresses in the interactions not looked up yet, so their ENS names (and so ENS avatars) are
 * known. `fetchEnsNames` keeps only the EVM addresses.
 */
function newAddressesOf(interactions: readonly AddressInteraction[], seen: Set<string>): AddressBookSimplePayload[] {
  const fresh = new Set(interactions.flatMap(({ source, target }) => [source, target]).filter(address => !seen.has(address)));
  for (const address of fresh)
    seen.add(address);
  return Array.from(fresh, address => ({ address, blockchain: null }));
}

export function useAddressInteractions(): {
  interactions: Readonly<Ref<readonly AddressInteraction[]>>;
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string | undefined>>;
  refresh: () => Promise<void>;
} {
  const { fetchEnsNames } = useEnsOperations();
  const interactions = shallowRef<AddressInteraction[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = ref<string>();
  const ensLookedUp = new Set<string>();

  async function refresh(): Promise<void> {
    if (get(loading))
      return;

    set(loading, true);
    set(error, undefined);
    try {
      const response = AddressInteractions.parse(await api.get<AddressInteraction[]>('/statistics/address_interactions'));
      set(interactions, response);
      startPromise(fetchEnsNames(newAddressesOf(response, ensLookedUp)));
    }
    catch (error_: unknown) {
      if (!isRequestCancellation(error_))
        set(error, getErrorMessage(error_));
    }
    finally {
      set(loading, false);
    }
  }

  return { error: readonly(error), interactions: readonly(interactions), loading: readonly(loading), refresh };
}
