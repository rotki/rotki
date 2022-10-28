import { useQueriedAddressApi } from '@/services/session/queried-addresses-api';
import {
  QueriedAddresses,
  QueriedAddressPayload
} from '@/services/session/types';
import { useMessageStore } from '@/store/message';

export const useQueriedAddressesStore = defineStore(
  'session/queriedAddresses',
  () => {
    const queriedAddresses = ref<QueriedAddresses>({});

    const { setMessage } = useMessageStore();
    const api = useQueriedAddressApi();
    const { t } = useI18n();

    async function addQueriedAddress(payload: QueriedAddressPayload) {
      try {
        set(queriedAddresses, await api.addQueriedAddress(payload));
      } catch (e: any) {
        setMessage({
          description: t(
            'actions.session.add_queriable_address.error.message',
            {
              message: e.message
            }
          ).toString()
        });
      }
    }

    async function deleteQueriedAddress(payload: QueriedAddressPayload) {
      try {
        set(queriedAddresses, await api.deleteQueriedAddress(payload));
      } catch (e: any) {
        setMessage({
          description: t(
            'actions.session.delete_queriable_address.error.message',
            {
              message: e.message
            }
          ).toString()
        });
      }
    }

    async function fetchQueriedAddresses() {
      try {
        set(queriedAddresses, await api.queriedAddresses());
      } catch (e: any) {
        setMessage({
          description: t(
            'actions.session.fetch_queriable_address.error.message',
            {
              message: e.message
            }
          ).toString()
        });
      }
    }

    const reset = () => {
      set(queriedAddresses, {});
    };

    return {
      queriedAddresses,
      addQueriedAddress,
      deleteQueriedAddress,
      fetchQueriedAddresses,
      reset
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useQueriedAddressesStore, import.meta.hot)
  );
}
