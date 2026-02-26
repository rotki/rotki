import type { QueriedAddresses, QueriedAddressPayload } from '@/types/session';
import { useQueriedAddressApi } from '@/composables/api/session/queried-addresses';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';

export const useQueriedAddressesStore = defineStore('session/queried-addresses', () => {
  const queriedAddresses = ref<QueriedAddresses>({});

  const { showErrorMessage } = useNotifications();
  const api = useQueriedAddressApi();
  const { t } = useI18n({ useScope: 'global' });

  async function addQueriedAddress(payload: QueriedAddressPayload): Promise<void> {
    try {
      set(queriedAddresses, await api.addQueriedAddress(payload));
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.session.add_queriable_address.error.message', {
        message: getErrorMessage(error),
      }));
    }
  }

  async function deleteQueriedAddress(payload: QueriedAddressPayload): Promise<void> {
    try {
      set(queriedAddresses, await api.deleteQueriedAddress(payload));
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.session.delete_queriable_address.error.message', {
        message: getErrorMessage(error),
      }));
    }
  }

  async function fetchQueriedAddresses(): Promise<void> {
    try {
      set(queriedAddresses, await api.queriedAddresses());
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.session.fetch_queriable_address.error.message', {
        message: getErrorMessage(error),
      }));
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
