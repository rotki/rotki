export const SyncWarningSource = {
  ONLINE_EVENTS: 'online_events',
} as const;

export type SyncWarningSource = (typeof SyncWarningSource)[keyof typeof SyncWarningSource];

export interface SyncWarning {
  source: SyncWarningSource;
  key: string;
  message: string;
}

export const useSyncWarningsStore = defineStore('shell/sync-warnings', () => {
  const warnings = ref<SyncWarning[]>([]);

  const hasWarnings = computed<boolean>(() => get(warnings).length > 0);

  const addWarning = (warning: SyncWarning): void => {
    const current = get(warnings);
    if (current.some(item => item.source === warning.source && item.key === warning.key))
      return;
    set(warnings, [...current, warning]);
  };

  const resetWarnings = (): void => {
    set(warnings, []);
  };

  return {
    addWarning,
    hasWarnings,
    resetWarnings,
    warnings,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSyncWarningsStore, import.meta.hot));
