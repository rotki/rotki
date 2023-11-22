export const useUpdateMessage = createSharedComposable(() => {
  const lastUsedVersion = useLocalStorage<string>('rotki.last_version', null);
  const showReleaseNotes = ref(false);

  const { appVersion } = storeToRefs(useMainStore());

  const link = computed(
    () => `https://github.com/rotki/rotki/releases/tag/${get(appVersion)}`
  );

  const setShowNotes = (appVersion: string, lastUsed: string): void => {
    if (!appVersion || appVersion.includes('dev')) {
      return;
    }
    if (!lastUsed || lastUsed !== appVersion) {
      set(showReleaseNotes, true);
      set(lastUsedVersion, appVersion);
    }
  };

  watch(appVersion, appVersion => {
    setShowNotes(appVersion, get(lastUsedVersion));
  });

  onMounted(() => {
    setShowNotes(get(appVersion), get(lastUsedVersion));
  });

  return {
    showReleaseNotes,
    link,
    version: appVersion
  };
});
