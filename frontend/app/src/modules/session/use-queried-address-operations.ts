import type { QueriedAddressPayload } from '@/modules/session/types';
import { useQueriedAddressApi } from '@/composables/api/session/queried-addresses';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useSessionMetadataStore } from '@/store/session/metadata';

interface UseQueriedAddressOperationsReturn {
  addQueriedAddress: (payload: QueriedAddressPayload) => Promise<void>;
  deleteQueriedAddress: (payload: QueriedAddressPayload) => Promise<void>;
  fetchQueriedAddresses: () => Promise<void>;
}

export function useQueriedAddressOperations(): UseQueriedAddressOperationsReturn {
  const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
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
  };
}
