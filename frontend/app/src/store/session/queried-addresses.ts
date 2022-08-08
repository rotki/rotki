import { ref } from '@vue/composition-api';
import { set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import i18n from '@/i18n';
import { useQueriedAddressApi } from '@/services/session/queried-addresses-api';
import {
  QueriedAddresses,
  QueriedAddressPayload
} from '@/services/session/types';
import { useMainStore } from '@/store/main';

export const useQueriedAddressesStore = defineStore(
  'session/queriedAddresses',
  () => {
    const queriedAddresses = ref<QueriedAddresses>({});

    const { setMessage } = useMainStore();
    const api = useQueriedAddressApi();

    async function addQueriedAddress(payload: QueriedAddressPayload) {
      try {
        set(queriedAddresses, await api.addQueriedAddress(payload));
      } catch (e: any) {
        setMessage({
          description: i18n
            .t('actions.session.add_queriable_address.error.message', {
              message: e.message
            })
            .toString()
        });
      }
    }

    async function deleteQueriedAddress(payload: QueriedAddressPayload) {
      try {
        set(queriedAddresses, await api.deleteQueriedAddress(payload));
      } catch (e: any) {
        setMessage({
          description: i18n
            .t('actions.session.delete_queriable_address.error.message', {
              message: e.message
            })
            .toString()
        });
      }
    }

    async function fetchQueriedAddresses() {
      try {
        set(queriedAddresses, await api.queriedAddresses());
      } catch (e: any) {
        setMessage({
          description: i18n
            .t('actions.session.fetch_queriable_address.error.message', {
              message: e.message
            })
            .toString()
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
