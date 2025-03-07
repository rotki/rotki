import type { QueriedAddresses, QueriedAddressPayload } from '@/types/session';
import { useQueriedAddressApi } from '@/composables/api/session/queried-addresses';
import { useMessageStore } from '@/store/message';

export const useQueriedAddressesStore = defineStore('session/queried-addresses', () => {
  const queriedAddresses = ref<QueriedAddresses>({});

  const { setMessage } = useMessageStore();
  const api = useQueriedAddressApi();
  const { t } = useI18n();

  async function addQueriedAddress(payload: QueriedAddressPayload): Promise<void> {
    try {
      set(queriedAddresses, await api.addQueriedAddress(payload));
    }
    catch (error: any) {
      setMessage({
        description: t('actions.session.add_queriable_address.error.message', {
          message: error.message,
        }),
      });
    }
  }

  async function deleteQueriedAddress(payload: QueriedAddressPayload): Promise<void> {
    try {
      set(queriedAddresses, await api.deleteQueriedAddress(payload));
    }
    catch (error: any) {
      setMessage({
        description: t('actions.session.delete_queriable_address.error.message', {
          message: error.message,
        }),
      });
    }
  }

  async function fetchQueriedAddresses(): Promise<void> {
    try {
      set(queriedAddresses, await api.queriedAddresses());
    }
    catch (error: any) {
      setMessage({
        description: t('actions.session.fetch_queriable_address.error.message', {
          message: error.message,
        }),
      });
    }
  }

  return {
    addQueriedAddress,
    deleteQueriedAddress,
    fetchQueriedAddresses,
    queriedAddresses,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useQueriedAddressesStore, import.meta.hot));
