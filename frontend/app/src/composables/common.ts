import { useDisplay as display, useTheme as vTheme } from 'vuetify';

export function useProxy() {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
}

export function useTheme() {
  const vtTheme = vTheme();
  const theme = vtTheme.current;
  const dark = computed(() => get(theme).dark);

  const appBarColor = computed(() => {
    if (!get(dark))
      return 'white';

    return undefined;
  });

  return {
    theme,
    dark,
    appBarColor,
  };
}

export const useDisplay = () => display();
