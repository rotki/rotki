import { useInterop } from '@/modules/shell/app/use-electron-interop';

export const useUpdateChecker = createSharedComposable(() => {
  const showUpdatePopup = useSessionStorage('rotki.update_available', false);

  const { checkForUpdates } = useInterop();

  const checkForUpdate = async (): Promise<void> => {
    set(showUpdatePopup, await checkForUpdates());
  };

  return {
    checkForUpdate,
    showUpdatePopup,
  };
});
