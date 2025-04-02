import { useDarkMode } from '@/composables/dark-mode';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { Theme } from '@rotki/common';

export const useThemeChecker = createSharedComposable(() => {
  const { selectedTheme } = storeToRefs(useFrontendSettingsStore());
  const { logged } = storeToRefs(useSessionAuthStore());
  const { updateDarkMode } = useDarkMode();

  const storedSelectedTheme = useLocalStorage<Theme>('rotki.selected_theme', Theme.AUTO);

  const preferredDark = ref<boolean>(false);

  function checkTheme(): void {
    const theme = get(logged) ? get(selectedTheme) : get(storedSelectedTheme);
    const dark = get(preferredDark);

    const enabled = theme === Theme.AUTO ? dark : theme === Theme.DARK;
    updateDarkMode(enabled);
  }

  function setPreferredDark(event: MediaQueryListEvent | MediaQueryList): void {
    set(preferredDark, event.matches);
  }

  const mediaChecker = window.matchMedia('(prefers-color-scheme: dark)');

  onBeforeMount(() => {
    setPreferredDark(mediaChecker);
    checkTheme();
    mediaChecker.addEventListener('change', setPreferredDark);
  });

  onUnmounted(() => {
    mediaChecker.removeEventListener('change', setPreferredDark);
  });

  watch(selectedTheme, (selectedTheme) => {
    if (get(logged)) {
      set(storedSelectedTheme, selectedTheme);
    }
  });

  watch([selectedTheme, preferredDark], () => {
    checkTheme();
  });
});
