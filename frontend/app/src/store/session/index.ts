import { promiseTimeout } from '@vueuse/core';
import {
  type CreateAccountPayload,
  IncompleteUpgradeError,
  type LoginCredentials,
  SyncConflictError,
  type UnlockPayload,
} from '@/types/login';
import { TaskType } from '@/types/task-type';
import { UserAccount, type UserSettingsModel } from '@/types/user';
import { api } from '@/services/rotkehlchen-api';
import type { Exchange } from '@/types/exchanges';
import type { SupportedLanguage } from '@/types/settings/frontend-settings';
import type { TaskMeta } from '@/types/task';
import type { ChangePasswordPayload } from '@/types/session';
import type { ActionStatus } from '@/types/action';

export const useSessionStore = defineStore('session', () => {
  const showUpdatePopup = ref<boolean>(false);
  const darkModeEnabled = ref<boolean>(false);
  const checkForAssetUpdate = ref<boolean>(false);

  const authStore = useSessionAuthStore();
  const { logged, username, syncConflict, conflictExist, incompleteUpgradeConflict, shouldFetchData }
    = storeToRefs(authStore);

  const { initialize } = useSessionSettings();
  const usersApi = useUsersApi();
  const settingsApi = useSettingsApi();
  const exchangeApi = useExchangeApi();

  const { setMessage } = useMessageStore();

  const { checkForUpdates, resetTray, isPackaged, clearPassword } = useInterop();
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

    return { success: false, message };
  };

  const unlock = ({ settings, exchanges, fetchData, username: user }: UnlockPayload): ActionStatus => {
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
      const { settings, exchanges } = UserAccount.parse(result);
      const data: UnlockPayload = {
        settings,
        exchanges,
        username: payload.credentials.username,
        fetchData: payload.premiumSetup?.syncDatabase,
      };
      return unlock(data);
    }
    catch (error: any) {
      logger.error(error);
      return { success: false, message: error.message };
    }
  };

  const login = async (credentials: LoginCredentials): Promise<ActionStatus> => {
    try {
      const username = credentials.username ? credentials.username : lastLogin();
      const isLogged = await usersApi.checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(conflictExist);

      if (isLogged && !conflict) {
        [settings, exchanges] = await Promise.all([settingsApi.getSettings(), exchangeApi.getExchanges()]);
      }
      else {
        if (!credentials.username)
          return { success: false, message: '' };

        authStore.resetSyncConflict();
        authStore.resetIncompleteUpgradeConflict();
        const taskType = TaskType.LOGIN;
        const { taskId } = await usersApi.login(credentials);
        start();
        const { result } = await awaitTask<UserAccount, TaskMeta>(taskId, taskType, {
          title: 'login in',
        });

        const account = UserAccount.parse(result);
        ({ settings, exchanges } = account);
      }

      return unlock({
        settings,
        exchanges,
        username,
        fetchData: true,
      });
    }
    catch (error: any) {
      logger.error(error);
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
        title: 'Logout failed',
        description: error.message,
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
        title: 'Remote session logout failure',
        description: error.message,
      });
      return { success: false, message: error.message };
    }
  };

  const checkForUpdate = async (): Promise<void> => {
    set(showUpdatePopup, await checkForUpdates());
  };

  const changePassword = async ({ currentPassword, newPassword }: ChangePasswordPayload): Promise<ActionStatus> => {
    try {
      const success = await usersApi.changeUserPassword(get(username), currentPassword, newPassword);
      setMessage({
        description: t('actions.session.password_change.success').toString(),
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
        }).toString(),
      });
      return {
        success: false,
        message: error.message,
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
    showUpdatePopup,
    darkModeEnabled,
    login,
    logout,
    logoutRemoteSession,
    createAccount,
    changePassword,
    checkForUpdate,
    checkForAssetUpdate,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionStore, import.meta.hot));
