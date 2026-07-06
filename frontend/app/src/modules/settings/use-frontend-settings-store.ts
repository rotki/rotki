import type { PendingSuggestion } from '@/modules/settings/suggestions/settings-suggestions';
import { toSettingsRefs } from '@/modules/core/common/to-settings-refs';
import { PrivacyMode } from '@/modules/session/types';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import {
  type FrontendSettings,
  getDefaultFrontendSettings,
} from '@/modules/settings/types/frontend-settings';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const settings = ref<FrontendSettings>(markRaw(getDefaultFrontendSettings()));

  // `schemaVersion` is internal bookkeeping and is intentionally not part of the public surface.
  const refs = toSettingsRefs(settings, ['schemaVersion']);

  const shouldShowAmount = computed(() => get(refs.privacyMode) < PrivacyMode.SEMI_PRIVATE);
  const shouldShowPercentage = computed(() => get(refs.privacyMode) < PrivacyMode.PRIVATE);

  const pendingSuggestions = ref<PendingSuggestion[]>([]);
  const showSuggestionsDialog = shallowRef<boolean>(false);

  const globalItemsPerPage = useItemsPerPage();

  function update(update: Partial<FrontendSettings>): void {
    set(settings, {
      ...get(settings),
      ...update,
    });
    const itemsPerPage = get(settings, 'itemsPerPage');
    if (itemsPerPage !== get(globalItemsPerPage))
      set(globalItemsPerPage, itemsPerPage);
  }

  return {
    ...refs,
    pendingSuggestions,
    settings,
    shouldShowAmount,
    shouldShowPercentage,
    showSuggestionsDialog,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot));
