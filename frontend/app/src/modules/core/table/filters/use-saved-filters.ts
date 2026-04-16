import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { BaseSuggestion, SavedFilterLocation, Suggestion } from '@/modules/core/table/filtering';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

const LIMIT_PER_LOCATION = 10;

interface UseSavedFilterReturn {
  savedFilters: ComputedRef<Suggestion[][]>;
  addFilter: (newFilter: Suggestion[]) => Promise<ActionStatus>;
  deleteFilter: (index: number) => Promise<void>;
  saveFilters: (filters: BaseSuggestion[][]) => Promise<ActionStatus>;
}

export function useSavedFilter(
  location: MaybeRefOrGetter<SavedFilterLocation>,
  isAsset: (key: string) => boolean,
): UseSavedFilterReturn {
  const frontendStore = useFrontendSettingsStore();
  const { updateFrontendSetting } = useSettingsOperations();

  const { savedFilters: allSavedFilters } = storeToRefs(frontendStore);

  const savedFilters = computed<Suggestion[][]>(() => {
    const baseSuggestions = get(allSavedFilters)[toValue(location)] || [];

    return baseSuggestions.map(suggestions =>
      suggestions.map(suggestion => ({
        ...suggestion,
        asset: isAsset(suggestion.key),
        index: 0,
        total: 1,
      })),
    );
  });

  const { t } = useI18n({ useScope: 'global' });

  const saveFilters = async (filters: BaseSuggestion[][]): Promise<ActionStatus> => {
    const allSaved = { ...get(allSavedFilters) };
    allSaved[toValue(location)] = filters;
    return updateFrontendSetting({
      savedFilters: allSaved,
    });
  };

  const addFilter = async (newFilter: Suggestion[]): Promise<ActionStatus> => {
    const currentFilters = get(allSavedFilters)[toValue(location)] || [];

    if (currentFilters.length >= LIMIT_PER_LOCATION) {
      return {
        message: t('table_filter.saved_filters.saving.limited', {
          limit: LIMIT_PER_LOCATION,
        }).toString(),
        success: false,
      };
    }

    const newFilters = [
      ...currentFilters,
      newFilter.map(item => ({
        exclude: item.exclude,
        key: item.key,
        value: !item.asset || typeof item.value === 'string' ? item.value : item.value.identifier,
      })),
    ];
    return saveFilters(newFilters);
  };

  const deleteFilter = async (index: number): Promise<void> => {
    const newFilters = [...get(savedFilters)];
    newFilters.splice(index, 1);

    await saveFilters(newFilters);
  };

  return {
    addFilter,
    deleteFilter,
    savedFilters,
    saveFilters,
  };
}
