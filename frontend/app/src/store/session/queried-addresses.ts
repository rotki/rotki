import {
  type QueriedAddressPayload,
  type QueriedAddresses
} from '@/types/session';

export const useQueriedAddressesStore = defineStore(
  'session/queried-addresses',
  () => {
    const queriedAddresses = ref<QueriedAddresses>({});

    const { setMessage } = useMessageStore();
    const api = useQueriedAddressApi();
    const { t } = useI18n();

    async function addQueriedAddress(
      payload: QueriedAddressPayload
    ): Promise<void> {
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

    async function deleteQueriedAddress(
      payload: QueriedAddressPayload
    ): Promise<void> {
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

    async function fetchQueriedAddresses(): Promise<void> {
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

    return {
      queriedAddresses,
      addQueriedAddress,
      deleteQueriedAddress,
      fetchQueriedAddresses
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useQueriedAddressesStore, import.meta.hot)
  );
}
