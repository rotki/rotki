import type { MaybeRefOrGetter, Ref } from 'vue';
import { useRememberSettings } from '@/modules/auth/use-remember-settings';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseLoginRememberOptionsOptions {
  /** Whether the app talks to a docker backend, which flips the remember-username default. */
  isDocker: MaybeRefOrGetter<boolean>;
}

interface UseLoginRememberOptionsReturn {
  /** Bound to the remember-username checkbox. */
  modelRememberUsername: Ref<boolean>;
  /** Bound to the remember-password checkbox, which only shows on packaged builds. */
  modelRememberPassword: Ref<boolean>;
  /** The username persisted by a previous session, used to suppress the initial touched emit. */
  storedUsername: Readonly<Ref<string>>;
  /** Restores both remember toggles from persisted settings. */
  loadRememberSettings: () => void;
  /** Persists username and password according to the current remember toggles. */
  rememberCredentials: (username: string, password: string) => Promise<void>;
}

/**
 * Owns the login form's "remember username/password" toggles and their persistence.
 *
 * The toggles are two-way bound in the template, so they are returned as writable
 * `model`-prefixed refs. Persistence is a side effect of flipping a toggle, which is why
 * the watchers live here rather than in the component.
 */
export function useLoginRememberOptions(options: UseLoginRememberOptionsOptions): UseLoginRememberOptionsReturn {
  const { isDocker } = options;

  const modelRememberUsername = shallowRef<boolean>(false);
  const modelRememberPassword = shallowRef<boolean>(false);

  const { savedRememberPassword, savedRememberUsername, savedUsername } = useRememberSettings();
  const { clearPassword, isPackaged, storePassword } = useInterop();

  function checkRememberUsername(): void {
    set(modelRememberUsername, !!get(savedRememberUsername) || !!get(savedRememberPassword) || !toValue(isDocker));
  }

  function loadRememberSettings(): void {
    set(modelRememberPassword, !!get(savedRememberPassword));
    checkRememberUsername();
  }

  async function rememberCredentials(username: string, password: string): Promise<void> {
    if (get(modelRememberUsername))
      set(savedUsername, username);

    if (get(modelRememberPassword) && isPackaged)
      await storePassword(username, password);
  }

  watch(modelRememberUsername, (remember: boolean, previous: boolean) => {
    if (remember === previous)
      return;

    if (!remember) {
      set(savedRememberUsername, null);
      set(savedUsername, null);
    }
    else {
      set(savedRememberUsername, 'true');
    }
  });

  watch(modelRememberPassword, async (remember: boolean, previous: boolean) => {
    if (remember === previous)
      return;

    if (!remember) {
      set(savedRememberPassword, null);
      if (isPackaged)
        await clearPassword();
    }
    else {
      set(savedRememberPassword, 'true');
    }

    checkRememberUsername();
  });

  return {
    loadRememberSettings,
    modelRememberPassword,
    modelRememberUsername,
    rememberCredentials,
    storedUsername: readonly(savedUsername),
  };
}
