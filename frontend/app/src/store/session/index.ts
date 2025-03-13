import { promiseTimeout } from '@vueuse/core';
import {
  type CreateAccountPayload,
  IncompleteUpgradeError,
  type LoginCredentials,
  SyncConflictError,
  type UnlockPayload,
} from '@/types/login';
import { TaskType } from '@/types/task-type';
import { type SettingsUpdate, UserAccount, UserSettingsModel } from '@/types/user';
import { api } from '@/services/rotkehlchen-api';
import { logger } from '@/utils/logging';
import { lastLogin } from '@/utils/account-management';
import { useMonitorStore } from '@/store/monitor';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { useMessageStore } from '@/store/message';
import { useSessionAuthStore } from '@/store/session/auth';
import { useAppNavigation } from '@/composables/navigation';
import { useLastLanguage } from '@/composables/session/language';
import { useInterop } from '@/composables/electron-interop';
import { useExchangeApi } from '@/composables/api/balances/exchanges';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { useUsersApi } from '@/composables/api/session/users';
import { useSessionSettings } from '@/composables/session/settings';
import { migrateSettingsIfNeeded } from '@/types/settings/frontend-settings-migrations';
import type { SupportedLanguage } from '@/types/settings/frontend-settings';
import type { Exchange } from '@/types/exchanges';
import type { TaskMeta } from '@/types/task';
import type { ChangePasswordPayload } from '@/types/session';
import type { ActionStatus } from '@/types/action';

export const useSessionStore = defineStore('session', () => {
  const showUpdatePopup = ref<boolean>(false);
  const darkModeEnabled = ref<boolean>(false);
  const checkForAssetUpdate = ref<boolean>(false);

  const authStore = useSessionAuthStore();
  const {
    conflictExist,
    incompleteUpgradeConflict,
    logged,
    shouldFetchData,
    syncConflict,
    username,
  } = storeToRefs(authStore);

  const { initialize } = useSessionSettings();
  const usersApi = useUsersApi();
  const settingsApi = useSettingsApi();
  const exchangeApi = useExchangeApi();

  const { setMessage } = useMessageStore();

  const { checkForUpdates, clearPassword, isPackaged, resetTray } = useInterop();
  const { awaitTask } = useTaskStore();

  const { t } = useI18n();
  const { start } = useMonitorStore();

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
      const { taskId } = await usersApi.createAccount(payload);
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

  async function migrateAndSaveSettings(frontendSettings?: string): Promise<string | undefined> {
    const migratedSettings = migrateSettingsIfNeeded(frontendSettings);

    if (migratedSettings) {
      await settingsApi.setSettings({ frontendSettings: migratedSettings });
      return migratedSettings;
    }
    return frontendSettings;
  }

  const login = async (credentials: LoginCredentials): Promise<ActionStatus> => {
    try {
      const username = credentials.username ? credentials.username : lastLogin();
      const isLogged = await usersApi.checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(conflictExist);

      if (isLogged && !conflict) {
        const [rawSettings, activeExchanges] = await Promise.all([
          settingsApi.getRawSettings(),
          exchangeApi.getExchanges(),
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
        const taskType = TaskType.LOGIN;
        const { taskId } = await usersApi.login(credentials);
        start();
        const { result } = await awaitTask<{
          settings: SettingsUpdate;
          exchanges: Exchange[];
        }, TaskMeta>(taskId, taskType, {
          title: 'login in',
        });

        result.settings.frontendSettings = await migrateAndSaveSettings(result.settings.frontendSettings);

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

  const { navigateToUserLogin } = useAppNavigation();

  const logout = async (navigate: boolean = true): Promise<void> => {
    set(logged, false);
    const user = get(username); // save the username, after the await below, it is reset
    // allow some time for the components to leave the dom completely and show loading overlay
    await promiseTimeout(1500);
    resetTray();
    try {
      await usersApi.logout(user);
    }
    catch (error: any) {
      logger.error(error);
      setMessage({
        description: error.message,
        title: 'Logout failed',
      });
    }

    if (navigate)
      await navigateToUserLogin();
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    try {
      const loggedUsers = await usersApi.loggedUsers();
      for (const user of loggedUsers) await usersApi.logout(user);

      return { success: true };
    }
    catch (error: any) {
      setMessage({
        description: error.message,
        title: 'Remote session logout failure',
      });
      return { message: error.message, success: false };
    }
  };

  const checkForUpdate = async (): Promise<void> => {
    set(showUpdatePopup, await checkForUpdates());
  };

  const changePassword = async ({ currentPassword, newPassword }: ChangePasswordPayload): Promise<ActionStatus> => {
    try {
      const success = await usersApi.changeUserPassword(get(username), currentPassword, newPassword);
      setMessage({
        description: t('actions.session.password_change.success'),
        success: true,
      });

      if (success && isPackaged) {
        clearPassword()
          .then(() => logger.info('clear complete'))
          .catch(error => logger.error(error));
      }

      return {
        success,
      };
    }
    catch (error: any) {
      setMessage({
        description: t('actions.session.password_change.error', {
          message: error.message,
        }),
      });
      return {
        message: error.message,
        success: false,
      };
    }
  };

  const { lastLanguage } = useLastLanguage();
  const { language } = storeToRefs(useFrontendSettingsStore());

  const adaptiveLanguage = computed<SupportedLanguage>(() => {
    const selectedLanguageVal = get(lastLanguage);
    return !get(logged) && selectedLanguageVal !== 'undefined'
      ? (selectedLanguageVal as SupportedLanguage)
      : get(language);
  });

  return {
    adaptiveLanguage,
    changePassword,
    checkForAssetUpdate,
    checkForUpdate,
    createAccount,
    darkModeEnabled,
    login,
    logout,
    logoutRemoteSession,
    showUpdatePopup,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionStore, import.meta.hot));
