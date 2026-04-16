import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useUpdateChecker } from '@/modules/session/use-update-checker';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useMonitorService } from '@/modules/shell/app/use-monitor-service';
import { useWebsocketConnection } from '@/modules/shell/app/use-websocket-connection';

interface UseLoginInitialChecksReturn {
  checkForAssetUpdate: Ref<boolean>;
  initialChecksDone: Ref<boolean>;
  performingInitialChecks: Ref<boolean>;
  performInitialChecks: () => Promise<void>;
  showUpgradeProgress: ComputedRef<boolean>;
  upgradeVisible: Ref<boolean>;
}

export function useLoginInitialChecks(errors: MaybeRefOrGetter<string[]>): UseLoginInitialChecksReturn {
  const { checkForAssetUpdate, upgradeVisible } = storeToRefs(useSessionAuthStore());
  const { checkForUpdate } = useUpdateChecker();
  const { isPackaged } = useInterop();
  const { connect } = useWebsocketConnection();
  const { startTaskMonitoring } = useMonitorService();

  const initialChecksDone = shallowRef<boolean>(false);
  const performingInitialChecks = shallowRef<boolean>(false);

  const showUpgradeProgress = computed<boolean>(() => get(upgradeVisible) && toValue(errors).length === 0);

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
