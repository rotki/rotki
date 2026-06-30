import { useUpdateChecker } from '@/modules/session/use-update-checker';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseLoginInitialChecksReturn {
  performInitialChecks: () => Promise<void>;
}

/**
 * Pre-login checks. Only the packaged app-update check runs before the user authenticates.
 * The WS connect, task monitoring, and the asset-update check moved into the post-authenticate
 * unlock flow (`useUnlockFlow`) so that no gated backend calls fire before login (fix #2 for
 * the Backend Sessions cookie gate).
 */
export function useLoginInitialChecks(): UseLoginInitialChecksReturn {
  const { checkForUpdate } = useUpdateChecker();
  const { isPackaged } = useInterop();

  async function performInitialChecks(): Promise<void> {
    if (isPackaged)
      await checkForUpdate();
  }

  return { performInitialChecks };
}
