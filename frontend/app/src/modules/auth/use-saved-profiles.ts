import type { ComputedRef, Ref } from 'vue';
import { createSharedComposable } from '@vueuse/core';
import { useUsersApi } from '@/modules/auth/use-users-api';

interface UseSavedProfilesReturn {
  savedUsernames: Ref<string[]>;
  hasProfiles: ComputedRef<boolean>;
  loadProfiles: () => Promise<void>;
}

export const useSavedProfiles = createSharedComposable((): UseSavedProfilesReturn => {
  const { getUserProfiles } = useUsersApi();
  const savedUsernames = ref<string[]>([]);

  const hasProfiles = computed<boolean>(() => get(savedUsernames).length > 0);

  const loadProfiles = async (): Promise<void> => {
    set(savedUsernames, await getUserProfiles());
  };

  return {
    hasProfiles,
    loadProfiles,
    savedUsernames,
  };
});
