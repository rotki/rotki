import type { ComputedRef, Ref } from 'vue';
import { createSharedComposable } from '@vueuse/core';
import { useRememberSettings } from '@/modules/auth/use-remember-settings';
import { useUsersApi } from '@/modules/auth/use-users-api';

interface UseSavedProfilesReturn {
  savedUsernames: Ref<string[]>;
  hasProfiles: ComputedRef<boolean>;
  loadProfiles: () => Promise<void>;
  resolveStoredUsername: () => string;
}

export const useSavedProfiles = createSharedComposable((): UseSavedProfilesReturn => {
  const { getUserProfiles } = useUsersApi();
  const { savedUsername } = useRememberSettings();
  const savedUsernames = ref<string[]>([]);

  const hasProfiles = computed<boolean>(() => get(savedUsernames).length > 0);

  const loadProfiles = async (): Promise<void> => {
    set(savedUsernames, await getUserProfiles());
  };

  const resolveStoredUsername = (): string => {
    const stored = get(savedUsername);
    if (!stored)
      return '';

    if (get(savedUsernames).includes(stored))
      return stored;

    set(savedUsername, '');
    return '';
  };

  return {
    hasProfiles,
    loadProfiles,
    resolveStoredUsername,
    savedUsernames,
  };
});
