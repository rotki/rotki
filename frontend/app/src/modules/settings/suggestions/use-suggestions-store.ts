import type { PendingSuggestion } from './settings-suggestions';

/**
 * Holds the UI state for the post-login settings-suggestions dialog.
 *
 * @remarks
 * Client-only view state, not a persisted setting, which is why it has its own store rather than
 * a slot in the frontend settings. `useSettingsSuggestions` fills it; `AppCore` renders from it.
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
