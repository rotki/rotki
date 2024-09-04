import type { MaybeRef } from '@vueuse/core';
import type { BaseSuggestion, SavedFilterLocation, Suggestion } from '@/types/filtering';
import type { ActionStatus } from '@/types/action';

const LIMIT_PER_LOCATION = 10;

interface UseSavedFilterReturn {
  savedFilters: ComputedRef<Suggestion[][]>;
  addFilter: (newFilter: Suggestion[]) => Promise<ActionStatus>;
  deleteFilter: (index: number) => Promise<void>;
  saveFilters: (filters: BaseSuggestion[][]) => Promise<ActionStatus>;
}

export function useSavedFilter(
  location: MaybeRef<SavedFilterLocation>,
  isAsset: (key: string) => boolean,
): UseSavedFilterReturn {
  const frontendStore = useFrontendSettingsStore();
  const { updateSetting } = frontendStore;

  const { savedFilters: allSavedFilters } = storeToRefs(frontendStore);

  const savedFilters = computed<Suggestion[][]>(() => {
    const baseSuggestions = get(allSavedFilters)[get(location)] || [];

    return baseSuggestions.map(suggestions =>
      suggestions.map(suggestion => ({
        ...suggestion,
        index: 0,
        total: 1,
        asset: isAsset(suggestion.key),
      })),
    );
  });

  const { t } = useI18n();

  const saveFilters = async (filters: BaseSuggestion[][]): Promise<ActionStatus> => {
    const allSaved = { ...get(allSavedFilters) };
    allSaved[get(location)] = filters;
    return await updateSetting({
      savedFilters: allSaved,
    });
  };

  const addFilter = async (newFilter: Suggestion[]): Promise<ActionStatus> => {
    const currentFilters = get(allSavedFilters)[get(location)] || [];

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
        key: item.key,
        value: !item.asset || typeof item.value === 'string' ? item.value : item.value.identifier,
        exclude: item.exclude,
      })),
    ];
    return await saveFilters(newFilters);
  };

  const deleteFilter = async (index: number): Promise<void> => {
    const newFilters = [...get(savedFilters)];
    newFilters.splice(index, 1);

    await saveFilters(newFilters);
  };

  return {
    savedFilters,
    addFilter,
    deleteFilter,
    saveFilters,
  };
}
