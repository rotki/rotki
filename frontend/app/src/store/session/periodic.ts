import { useSessionApi } from '@/services/session';
import { backoff } from '@/utils/backoff';

export const usePeriodicStore = defineStore('session/periodic', () => {
  const lastBalanceSave = ref(0);
  const lastDataUpload = ref(0);
  const connectedEthNodes = ref<string[]>([]);
  const connectedOptimismNodes = ref<string[]>([]);
  const periodicRunning = ref(false);

  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const { fetchPeriodicData } = useSessionApi();

  const check = async (): Promise<void> => {
    if (get(periodicRunning)) {
      return;
    }
    set(periodicRunning, true);
    try {
      const result = await backoff(3, () => fetchPeriodicData(), 10000);
      if (Object.keys(result).length === 0) {
        // an empty object means user is not logged in yet
        return;
      }

      const {
        lastBalanceSave: balance,
        lastDataUploadTs: upload,
        connectedEthNodes: ethNodes,
        connectedOptimismNodes: optimismNodes
      } = result;

      if (get(lastBalanceSave) !== balance) {
        set(lastBalanceSave, balance);
      }

      if (get(lastDataUpload) !== upload) {
        set(lastDataUpload, upload);
      }

      set(connectedEthNodes, ethNodes);
      set(connectedOptimismNodes, optimismNodes);
    } catch (e: any) {
      notify({
        title: t('actions.session.periodic_query.error.title').toString(),
        message: t('actions.session.periodic_query.error.message', {
          message: e.message
        }).toString(),
        display: true
      });
    } finally {
      set(periodicRunning, false);
    }
  };

  return {
    lastBalanceSave,
    lastDataUpload,
    connectedEthNodes,
    connectedOptimismNodes,
    check
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(usePeriodicStore, import.meta.hot));
}
