export function useProxy() {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
}

export function useTheme() {
  const { $vuetify } = useProxy();
  const theme = computed(() => $vuetify.theme);
  const dark = computed(() => $vuetify.theme.dark);

  const appBarColor = computed(() => {
    if (!get(dark))
      return 'white';

    return null;
  });

  return {
    $vuetify,
    theme,
    dark,
    appBarColor,
  };
}
