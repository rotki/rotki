import type { ComputedRef, Ref } from 'vue';
import { useInterop } from '@/composables/electron-interop';
import { useUpdateChecker } from '@/modules/session/use-update-checker';
import { useMonitorStore } from '@/store/monitor';
import { useSessionAuthStore } from '@/store/session/auth';
import { useWebsocketStore } from '@/store/websocket';

interface UseLoginInitialChecksReturn {
  checkForAssetUpdate: Ref<boolean>;
  initialChecksDone: Ref<boolean>;
  performingInitialChecks: Ref<boolean>;
  performInitialChecks: () => Promise<void>;
  showUpgradeProgress: ComputedRef<boolean>;
  upgradeVisible: Ref<boolean>;
}

export function useLoginInitialChecks(errors: Ref<string[]>): UseLoginInitialChecksReturn {
  const { checkForAssetUpdate, upgradeVisible } = storeToRefs(useSessionAuthStore());
  const { checkForUpdate } = useUpdateChecker();
  const { isPackaged } = useInterop();
  const { connect } = useWebsocketStore();
  const { startTaskMonitoring } = useMonitorStore();

  const initialChecksDone = ref<boolean>(false);
  const performingInitialChecks = ref<boolean>(false);

  const showUpgradeProgress = computed<boolean>(() => get(upgradeVisible) && get(errors).length === 0);

  async function performInitialChecks(): Promise<void> {
    set(performingInitialChecks, true);

    try {
      // Check for app updates before showing login form
      if (isPackaged)
        await checkForUpdate();

      // Connect to backend and start monitoring before showing asset update UI
      await connect();
      startTaskMonitoring(false);

      // Set checkForAssetUpdate to true first, so AssetUpdate component will be shown and can run its check
      set(checkForAssetUpdate, true);

      // Mark initial checks as done after setting checkForAssetUpdate
      // This ensures AssetUpdate component is shown with the flag already set
      set(initialChecksDone, true);
    }
    finally {
      set(performingInitialChecks, false);
    }
  }

  return {
    checkForAssetUpdate,
    initialChecksDone,
    performingInitialChecks,
    performInitialChecks,
    showUpgradeProgress,
    upgradeVisible,
  };
}
