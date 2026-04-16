import { backoff } from '@shared/utils';
import { useSessionApi } from '@/composables/api/session';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

interface UsePeriodicDataFetcherReturn {
  check: () => Promise<void>;
}

export function usePeriodicDataFetcher(): UsePeriodicDataFetcherReturn {
  const periodicRunning = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  const store = useSessionMetadataStore();
  const { connectedNodes, coolingDownNodes, failedToConnect, lastBalanceSave, lastDataUpload } = storeToRefs(store);

  const { notifyError } = useNotifications();
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

      const {
        connectedNodes: connected,
        coolingDownNodes: cooling,
        failedToConnect: failed,
        lastBalanceSave: balance,
        lastDataUploadTs: upload,
      } = result;

      if (get(lastBalanceSave) !== balance)
        set(lastBalanceSave, balance);

      if (get(lastDataUpload) !== upload)
        set(lastDataUpload, upload);

      set(connectedNodes, connected);
      set(coolingDownNodes, cooling ?? {});
      set(failedToConnect, failed ?? {});
    }
    catch (error: unknown) {
      notifyError(
        t('actions.session.periodic_query.error.title'),
        t('actions.session.periodic_query.error.message', {
          message: getErrorMessage(error),
        }),
      );
    }
    finally {
      set(periodicRunning, false);
    }
  };

  return {
    check,
  };
}
