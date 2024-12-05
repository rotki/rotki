import { backoff } from '@shared/utils';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionApi } from '@/composables/api/session';

export const usePeriodicStore = defineStore('session/periodic', () => {
  const lastBalanceSave = ref(0);
  const lastDataUpload = ref(0);
  const connectedNodes = ref<Record<string, string[]>>({});
  const periodicRunning = ref(false);

  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const { fetchPeriodicData } = useSessionApi();

  const check = async (): Promise<void> => {
    if (get(periodicRunning))
      return;

    set(periodicRunning, true);
    try {
      const result = await backoff(3, async () => fetchPeriodicData(), 10000);
      if (Object.keys(result).length === 0) {
        // an empty object means user is not logged in yet
        return;
      }

      const { connectedNodes: connected, lastBalanceSave: balance, lastDataUploadTs: upload } = result;

      if (get(lastBalanceSave) !== balance)
        set(lastBalanceSave, balance);

      if (get(lastDataUpload) !== upload)
        set(lastDataUpload, upload);

      set(connectedNodes, connected);
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('actions.session.periodic_query.error.message', {
          message: error.message,
        }),
        title: t('actions.session.periodic_query.error.title'),
      });
    }
    finally {
      set(periodicRunning, false);
    }
  };

  return {
    check,
    connectedNodes,
    lastBalanceSave,
    lastDataUpload,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(usePeriodicStore, import.meta.hot));
