import type { LidoCsmNodeOperator, LidoCsmNodeOperatorPayload } from '@/types/staking';
import { useLidoCsmApi } from '@/composables/api/staking/lido-csm';
import { useMessageStore } from '@/store/message';

export const useLidoCsmStore = defineStore('staking/lido-csm', () => {
  const nodeOperators = ref<LidoCsmNodeOperator[]>([]);
  const loading = ref<boolean>(false);

  const api = useLidoCsmApi();
  const { setMessage } = useMessageStore();
  const { t } = useI18n({ useScope: 'global' });

  async function fetchNodeOperators(): Promise<void> {
    set(loading, true);
    try {
      set(nodeOperators, await api.listNodeOperators());
    }
    catch (error: any) {
      setMessage({
        description: t('staking_page.lido_csm.messages.fetch_failed', { message: error.message }),
      });
    }
    finally {
      set(loading, false);
    }
  }

  async function addNodeOperator(payload: LidoCsmNodeOperatorPayload): Promise<void> {
    try {
      set(nodeOperators, await api.addNodeOperator(payload));
    }
    catch (error: any) {
      setMessage({
        description: t('staking_page.lido_csm.messages.add_failed', { message: error.message }),
      });
      throw error;
    }
  }

  async function deleteNodeOperator(payload: LidoCsmNodeOperatorPayload): Promise<void> {
    try {
      set(nodeOperators, await api.deleteNodeOperator(payload));
    }
    catch (error: any) {
      setMessage({
        description: t('staking_page.lido_csm.messages.delete_failed', { message: error.message }),
      });
      throw error;
    }
  }

  return {
    addNodeOperator,
    deleteNodeOperator,
    fetchNodeOperators,
    loading,
    nodeOperators,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLidoCsmStore, import.meta.hot));
