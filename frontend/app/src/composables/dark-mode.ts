import { useSessionStore } from '@/store/session';

export const useDarkMode = () => {
  const store = useSessionStore();
  const { darkModeEnabled } = storeToRefs(store);

  const updateDarkMode = (enabled: boolean) => {
    set(darkModeEnabled, enabled);
  };

  return {
    darkModeEnabled,
    updateDarkMode
  };
};
