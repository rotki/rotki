import type { RemovableRef } from '@vueuse/core';

interface UseRememberSettingsReturn {
  savedRememberUsername: RemovableRef<string | null>;
  savedRememberPassword: RemovableRef<string | null>;
  savedUsername: RemovableRef<string>;
}

export function useRememberSettings(): UseRememberSettingsReturn {
  const savedRememberUsername = useLocalStorage<string | null>('rotki.remember_username', null);
  const savedRememberPassword = useLocalStorage<string | null>('rotki.remember_password', null);
  const savedUsername = useLocalStorage<string>('rotki.username', '');

  return {
    savedRememberPassword,
    savedRememberUsername,
    savedUsername,
  };
}
