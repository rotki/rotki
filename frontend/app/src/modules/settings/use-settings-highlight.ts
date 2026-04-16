import type { SettingsCategoryId, SettingsHighlightId } from '@/modules/settings/setting-highlight-ids';

export interface HighlightRequest {
  categoryId: SettingsCategoryId | SettingsHighlightId;
  highlightId?: SettingsHighlightId;
}

export const useSettingsHighlight = createSharedComposable(() => {
  const highlightTarget = ref<HighlightRequest>();

  function requestHighlight(categoryId: SettingsCategoryId | SettingsHighlightId, highlightId?: SettingsHighlightId): void {
    set(highlightTarget, { categoryId, highlightId });
  }

  function clearHighlight(): void {
    set(highlightTarget, undefined);
  }

  return {
    clearHighlight,
    highlightTarget,
    requestHighlight,
  };
});
