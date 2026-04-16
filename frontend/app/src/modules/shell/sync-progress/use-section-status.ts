import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { Section, Status } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';

export { Section, Status };

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

export async function waitUntilIdle(section: Section, subsection?: string): Promise<void> {
  const { getIsLoading } = useStatusStore();
  if (getIsLoading(section, subsection))
    await until(() => getIsLoading(section, subsection)).toBe(false);
}
