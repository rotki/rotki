import type { PendingSuggestion } from './settings-suggestions';

/**
 * UI state for the post-login settings-suggestions dialog. This was previously squatting in the
 * frontend settings store; it is client-only view state, not a persisted setting, so it lives on
 * its own store. `useSettingsSuggestions` fills it and `AppCore` renders from it.
 */
export const useSuggestionsStore = defineStore('settings/suggestions', () => {
  const pendingSuggestions = ref<PendingSuggestion[]>([]);
  const showSuggestionsDialog = shallowRef<boolean>(false);

  return {
    pendingSuggestions,
    showSuggestionsDialog,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSuggestionsStore, import.meta.hot));
