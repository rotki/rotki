import type { Ref } from 'vue';
import type { AddressInteraction } from './address-interaction-types';
import { z } from 'zod';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { api } from '@/modules/core/api/rotki-api';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';

const AddressInteractions = z.array(z.object({
  chain: z.string(),
  source: z.string(),
  target: z.string(),
  txHash: z.string(),
}));

export function useAddressInteractions(): {
  interactions: Readonly<Ref<readonly AddressInteraction[]>>;
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string | undefined>>;
  refresh: () => Promise<void>;
} {
  const interactions = ref<AddressInteraction[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = ref<string>();

  async function refresh(): Promise<void> {
    if (get(loading))
      return;

    set(loading, true);
    set(error, undefined);
    try {
      const response = await api.get<AddressInteraction[]>('/statistics/address_interactions');
      set(interactions, AddressInteractions.parse(response));
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
