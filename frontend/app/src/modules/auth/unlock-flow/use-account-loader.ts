import type { Exchange } from '@/modules/balances/types/exchanges';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { completeStoredSettings } from '@/modules/settings/types/frontend-settings-migrations';
import { UserAccount, UserSettingsModel } from '@/modules/settings/types/user-settings';

/** The account an unlock produced, for `loadSession` to hydrate the session with. */
export interface LoadedAccount {
  settings: UserSettingsModel;
  exchanges: Exchange[];
  fetchData: boolean;
  username: string;
  /** Set by `createUnlock`. Suppresses the settings-suggestions dialog for a fresh account. */
  newAccount?: boolean;
}

interface UseAccountLoaderReturn {
  parseAccount: (response: { exchanges: Exchange[]; settings: object }) => Promise<UserAccount>;
  resumeSession: (name: string) => Promise<LoadedAccount>;
}

/**
 * Reads the settings and exchanges an unlocked account carries, completing the frontend settings
 * on the way.
 */
export function useAccountLoader(): UseAccountLoaderReturn {
  const { getFrontendSettings, getRawSettings, patchFrontendSettings } = useSettingsApi();
  const { getExchanges } = useExchangeApi();

  /**
   * Reads the frontend settings and persists what {@link completeStoredSettings} says is missing.
   *
   * @remarks
   * Only logs on a failed write: parsing migrates in memory, so a login must not hinge on it.
   */
  async function loadFrontendSettings(): Promise<Record<string, unknown>> {
    const { settings, write } = completeStoredSettings(await getFrontendSettings());
    if (write !== undefined) {
      try {
        await patchFrontendSettings(write.patch, write.remove);
      }
      catch (error: unknown) {
        logger.error('failed to write back the frontend settings', error);
      }
    }
    return settings;
  }

  /** Loads an account whose session the backend already holds. */
  async function resumeSession(name: string): Promise<LoadedAccount> {
    const [rawSettings, frontendSettings, exchanges] = await Promise.all([
      getRawSettings(),
      loadFrontendSettings(),
      getExchanges(),
    ]);
    return {
      exchanges,
      fetchData: true,
      settings: UserSettingsModel.parse({ ...rawSettings, frontendSettings }),
      username: name,
    };
  }

  /**
   * Parses a login or account-creation response, splicing in the frontend settings it lacks.
   *
   * @remarks
   * Without them `initialize` skips the whole frontend hydration.
   */
  async function parseAccount(response: { exchanges: Exchange[]; settings: object }): Promise<UserAccount> {
    const frontendSettings = await loadFrontendSettings();
    return UserAccount.parse({
      ...response,
      settings: { ...response.settings, frontendSettings },
    });
  }

  return {
    parseAccount,
    resumeSession,
  };
}
