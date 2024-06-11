export function useProxy() {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
}

export function useTheme() {
  const { $vuetify } = useProxy();
  const theme = computed(() => $vuetify.theme);

  return {
    $vuetify,
    theme,
  };
}
