import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Section } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';

interface UseSectionStatusReturn {
  isInitialLoading: ComputedRef<boolean>;
  isLoading: ComputedRef<boolean>;
}

export function useSectionStatus(
  section: MaybeRefOrGetter<Section>,
  subsection?: MaybeRefOrGetter<string>,
): UseSectionStatusReturn {
  const { useIsLoading, useShouldShowLoadingScreen } = useStatusStore();
  return {
    isInitialLoading: useShouldShowLoadingScreen(section, subsection),
    isLoading: useIsLoading(section, subsection),
  };
}
