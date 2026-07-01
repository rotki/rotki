import type { UnlockCredentials } from './use-unlock-flow';
import { none, type OptionType as Option, some } from 'plainfp';
import { lastLogin } from '@/modules/auth/account-management';
import { useRememberSettings } from '@/modules/auth/use-remember-settings';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

export interface UseStoredCredentialsReturn {
  resolveStoredCredentials: () => Promise<Option<UnlockCredentials>>;
}

/**
 * Resolves the credentials for a background auto-unlock from local state only: the username
 * from the last login, and the password from the OS keychain when the app is packaged and
 * remember-password is on. Returns `none` when there is no saved profile — the flow then
 * shows the manual login form. Kept separate from the flow steps so the keychain/remember
 * sourcing is unit-testable on its own.
 */
export function useStoredCredentials(): UseStoredCredentialsReturn {
  const { getPassword, isPackaged } = useInterop();
  const { savedRememberPassword } = useRememberSettings();

  const resolveStoredCredentials = async (): Promise<Option<UnlockCredentials>> => {
    const username = get<string>(lastLogin);
    if (!username)
      return none;
    const password = isPackaged && get(savedRememberPassword)
      ? (await getPassword(username)) ?? ''
      : '';
    return some({ password, username });
  };

  return { resolveStoredCredentials };
}
