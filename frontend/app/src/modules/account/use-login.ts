import type { TaskMeta } from '@/modules/tasks/types';
import type { ActionStatus } from '@/types/action';
import type { Exchange } from '@/types/exchanges';
import { objectPick } from '@vueuse/shared';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useUsersApi } from '@/composables/api/session/users';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { useSessionSettings } from '@/composables/session/settings';
import { api } from '@/modules/api/rotki-api';
import { useMonitorService } from '@/modules/app/use-monitor-service';
import { sigilBus } from '@/modules/sigil/event-bus';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useSessionAuthStore } from '@/store/session/auth';
import {
  type CreateAccountPayload,
  IncompleteUpgradeError,
  type LoginCredentials,
  SyncConflictError,
  type UnlockPayload,
} from '@/types/login';
import { migrateSettingsIfNeeded } from '@/types/settings/frontend-settings-migrations';
import { type SettingsUpdate, UserAccount, UserSettingsModel } from '@/types/user';
import { lastLogin } from '@/utils/account-management';
import { getErrorMessage } from '@/utils/error-handling';
import { logger } from '@/utils/logging';

interface UseLoginReturn {
  login: (credentials: LoginCredentials) => Promise<ActionStatus>;
  createAccount: (payload: CreateAccountPayload) => Promise<ActionStatus>;
}

export function useLogin(): UseLoginReturn {
  const authStore = useSessionAuthStore();
  const {
    conflictExist,
    incompleteUpgradeConflict,
    logged,
    shouldFetchData,
    syncConflict,
    username,
  } = storeToRefs(authStore);
  const { runTask } = useTaskHandler();

  const { initialize } = useSessionSettings();
  const { checkIfLogged, colibriLogin, createAccount: callCreatAccount, login: callLogin } = useUsersApi();
  const { getRawSettings, setSettings } = useSettingsApi();
  const { getExchanges } = useExchangeApi();

  api.setOnAuthFailure(() => {
    set(logged, false);
  });

  const createActionStatus = (error: unknown): ActionStatus => {
    let message = '';
    if (error instanceof IncompleteUpgradeError) {
      set(incompleteUpgradeConflict, {
        message: error.message,
      });
    }
    else if (error instanceof SyncConflictError) {
      set(syncConflict, {
        message: error.message,
        payload: error.payload,
      });
    }
    else {
      message = getErrorMessage(error);
    }

    return { message, success: false };
  };

  const unlock = async ({ exchanges, fetchData, settings, username: user }: UnlockPayload): Promise<ActionStatus> => {
    try {
      await initialize(settings, exchanges);
      set(username, user);
      set(logged, true);
      if (fetchData)
        set(shouldFetchData, true);

      sigilBus.emit('session:ready');

      return { success: true };
    }
    catch (error: unknown) {
      logger.error(error);
      return createActionStatus(error);
    }
  };

  const createAccount = async (payload: CreateAccountPayload): Promise<ActionStatus> => {
    useMonitorService().start();
    const outcome = await runTask<UserAccount, TaskMeta>(
      async () => callCreatAccount(payload),
      { type: TaskType.CREATE_ACCOUNT, meta: { title: 'creating account' } },
    );

    if (outcome.success) {
      const { exchanges, settings } = UserAccount.parse(outcome.result);
      const data: UnlockPayload = {
        exchanges,
        fetchData: payload.premiumSetup?.syncDatabase,
        settings,
        username: payload.credentials.username,
      };
      const response = await unlock(data);
      await colibriLogin(objectPick(payload.credentials, ['username', 'password']));
      return response;
    }

    if (isActionableFailure(outcome))
      logger.error(outcome.error);

    return { message: outcome.message, success: false };
  };

  async function migrateAndSaveSettings(frontendSettings?: string): Promise<string | undefined> {
    const migratedSettings = migrateSettingsIfNeeded(frontendSettings);

    if (migratedSettings) {
      await setSettings({ frontendSettings: migratedSettings });
      return migratedSettings;
    }
    return frontendSettings;
  }

  const login = async (credentials: LoginCredentials): Promise<ActionStatus> => {
    try {
      const username = credentials.username ? credentials.username : get(lastLogin);
      const isLogged = await checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(conflictExist);

      if (isLogged && !conflict) {
        const [rawSettings, activeExchanges] = await Promise.all([
          getRawSettings(),
          getExchanges(),
        ]);

        rawSettings.frontendSettings = await migrateAndSaveSettings(rawSettings.frontendSettings);
        exchanges = activeExchanges;
        settings = UserSettingsModel.parse(rawSettings);
      }
      else {
        if (!credentials.username)
          return { message: '', success: false };

        authStore.resetSyncConflict();
        authStore.resetIncompleteUpgradeConflict();
        useMonitorService().start();
        const outcome = await runTask<{
          settings: SettingsUpdate;
          exchanges: Exchange[];
        }, TaskMeta>(
          async () => callLogin(credentials),
          { type: TaskType.LOGIN, meta: { title: 'login in' } },
        );

        if (!outcome.success) {
          if (isActionableFailure(outcome))
            throw new Error(outcome.message);
          return { message: '', success: false };
        }

        await colibriLogin(objectPick(credentials, ['username', 'password']));

        outcome.result.settings.frontendSettings = await migrateAndSaveSettings(outcome.result.settings.frontendSettings);

        const account = UserAccount.parse(outcome.result);
        ({ exchanges, settings } = account);
      }

      return await unlock({
        exchanges,
        fetchData: true,
        settings,
        username,
      });
    }
    catch (error: unknown) {
      logger.error(error);
      authStore.clearUpgradeMessages();
      return createActionStatus(error);
    }
  };

  return {
    createAccount,
    login,
  };
}
