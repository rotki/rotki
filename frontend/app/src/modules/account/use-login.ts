import type { ActionStatus } from '@/types/action';
import type { Exchange } from '@/types/exchanges';
import type { TaskMeta } from '@/types/task';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useUsersApi } from '@/composables/api/session/users';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { useSessionSettings } from '@/composables/session/settings';
import { api } from '@/services/rotkehlchen-api';
import { useMonitorStore } from '@/store/monitor';
import { useSessionAuthStore } from '@/store/session/auth';
import { useTaskStore } from '@/store/tasks';
import {
  type CreateAccountPayload,
  IncompleteUpgradeError,
  type LoginCredentials,
  SyncConflictError,
  type UnlockPayload,
} from '@/types/login';
import { migrateSettingsIfNeeded } from '@/types/settings/frontend-settings-migrations';
import { TaskType } from '@/types/task-type';
import { type SettingsUpdate, UserAccount, type UserSettingsModel } from '@/types/user';
import { lastLogin } from '@/utils/account-management';
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
  const { awaitTask } = useTaskStore();
  const { start } = useMonitorStore();

  const { initialize } = useSessionSettings();
  const { checkIfLogged, createAccount: callCreatAccount, login: callLogin } = useUsersApi();
  const { getSettings, setSettings } = useSettingsApi();
  const { getExchanges } = useExchangeApi();

  api.setOnAuthFailure(() => {
    set(logged, false);
  });

  const createActionStatus = (error: any): ActionStatus => {
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
      message = error.message;
    }

    return { message, success: false };
  };

  const unlock = ({ exchanges, fetchData, settings, username: user }: UnlockPayload): ActionStatus => {
    try {
      initialize(settings, exchanges);
      set(username, user);
      set(logged, true);
      if (fetchData)
        set(shouldFetchData, true);

      return { success: true };
    }
    catch (error: any) {
      logger.error(error);
      return createActionStatus(error);
    }
  };

  const createAccount = async (payload: CreateAccountPayload): Promise<ActionStatus> => {
    try {
      start();
      const taskType = TaskType.CREATE_ACCOUNT;
      const { taskId } = await callCreatAccount(payload);
      const { result } = await awaitTask<UserAccount, TaskMeta>(taskId, taskType, {
        title: 'creating account',
      });
      const { exchanges, settings } = UserAccount.parse(result);
      const data: UnlockPayload = {
        exchanges,
        fetchData: payload.premiumSetup?.syncDatabase,
        settings,
        username: payload.credentials.username,
      };
      return unlock(data);
    }
    catch (error: any) {
      logger.error(error);
      return { message: error.message, success: false };
    }
  };

  const login = async (credentials: LoginCredentials): Promise<ActionStatus> => {
    try {
      const username = credentials.username ? credentials.username : lastLogin();
      const isLogged = await checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(conflictExist);

      if (isLogged && !conflict) {
        [settings, exchanges] = await Promise.all([getSettings(), getExchanges()]);
      }
      else {
        if (!credentials.username)
          return { message: '', success: false };

        authStore.resetSyncConflict();
        authStore.resetIncompleteUpgradeConflict();
        const taskType = TaskType.LOGIN;
        const { taskId } = await callLogin(credentials);
        start();
        const { result } = await awaitTask<{
          settings: SettingsUpdate;
          exchanges: Exchange[];
        }, TaskMeta>(taskId, taskType, {
          title: 'login in',
        });

        const migratedSettings = migrateSettingsIfNeeded(result.settings.frontendSettings);

        if (migratedSettings) {
          await setSettings({ frontendSettings: migratedSettings });
          result.settings.frontendSettings = migratedSettings;
        }

        const account = UserAccount.parse(result);
        ({ exchanges, settings } = account);
      }

      return unlock({
        exchanges,
        fetchData: true,
        settings,
        username,
      });
    }
    catch (error: any) {
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
