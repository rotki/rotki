import { type ComputedRef } from 'vue';
import { type Exchange } from '@/types/exchanges';
import { type SupportedLanguage } from '@/types/frontend-settings';
import {
  type CreateAccountPayload,
  IncompleteUpgradeError,
  type LoginCredentials,
  SyncConflictError,
  type UnlockPayload
} from '@/types/login';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { UserAccount, type UserSettingsModel } from '@/types/user';
import { type ChangePasswordPayload } from '@/types/session';
import { type ActionStatus } from '@/types/action';

export const useSessionStore = defineStore('session', () => {
  const showUpdatePopup: Ref<boolean> = ref(false);
  const darkModeEnabled: Ref<boolean> = ref(false);
  const checkForAssetUpdate: Ref<boolean> = ref(false);

  const authStore = useSessionAuthStore();
  const {
    logged,
    username,
    syncConflict,
    conflictExist,
    incompleteUpgradeConflict,
    shouldFetchData
  } = storeToRefs(authStore);

  const { initialize } = useSessionSettings();
  const usersApi = useUsersApi();
  const settingsApi = useSettingsApi();
  const exchangeApi = useExchangeApi();

  const { setMessage } = useMessageStore();

  const { checkForUpdates, resetTray, isPackaged, clearPassword } =
    useInterop();
  const { awaitTask } = useTaskStore();

  const { t } = useI18n();
  const { start } = useMonitorStore();

  const unlock = async ({
    settings,
    exchanges,
    fetchData,
    username: user
  }: UnlockPayload): Promise<ActionStatus> => {
    try {
      initialize(settings, exchanges);
      set(username, user);
      set(logged, true);
      if (fetchData) {
        set(shouldFetchData, true);
      }

      return { success: true };
    } catch (e: any) {
      logger.error(e);
      return createActionStatus(e);
    }
  };

  const createAccount = async (
    payload: CreateAccountPayload
  ): Promise<ActionStatus> => {
    try {
      start();
      const taskType = TaskType.CREATE_ACCOUNT;
      const { taskId } = await usersApi.createAccount(payload);
      const { result } = await awaitTask<UserAccount, TaskMeta>(
        taskId,
        taskType,
        {
          title: 'creating account'
        }
      );
      const { settings, exchanges } = UserAccount.parse(result);
      const data: UnlockPayload = {
        settings,
        exchanges,
        username: payload.credentials.username,
        fetchData: payload.premiumSetup?.syncDatabase
      };
      return await unlock(data);
    } catch (e: any) {
      logger.error(e);
      return { success: false, message: e.message };
    }
  };

  const createActionStatus = (error: any): ActionStatus => {
    let message = '';
    if (error instanceof IncompleteUpgradeError) {
      set(incompleteUpgradeConflict, {
        message: error.message
      });
    } else if (error instanceof SyncConflictError) {
      set(syncConflict, {
        message: error.message,
        payload: error.payload
      });
    } else {
      message = error.message;
    }

    return { success: false, message };
  };

  const login = async (
    credentials: LoginCredentials
  ): Promise<ActionStatus> => {
    try {
      const username = credentials.username
        ? credentials.username
        : lastLogin();
      const isLogged = await usersApi.checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(conflictExist);

      if (isLogged && !conflict) {
        [settings, exchanges] = await Promise.all([
          settingsApi.getSettings(),
          exchangeApi.getExchanges()
        ]);
      } else {
        if (!credentials.username) {
          return { success: false, message: '' };
        }
        authStore.resetSyncConflict();
        authStore.resetIncompleteUpgradeConflict();
        const taskType = TaskType.LOGIN;
        const { taskId } = await usersApi.login(credentials);
        start();
        const { result } = await awaitTask<UserAccount, TaskMeta>(
          taskId,
          taskType,
          {
            title: 'login in'
          }
        );

        const account = UserAccount.parse(result);
        ({ settings, exchanges } = account);
      }

      return await unlock({
        settings,
        exchanges,
        username,
        fetchData: true
      });
    } catch (e: any) {
      logger.error(e);
      return createActionStatus(e);
    }
  };

  const logout = async (): Promise<void> => {
    resetTray();
    try {
      await usersApi.logout(get(username));
      set(logged, false);
    } catch (e: any) {
      setMessage({
        title: 'Logout failed',
        description: e.message
      });
    }
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    try {
      const loggedUsers = await usersApi.loggedUsers();
      for (const user of loggedUsers) {
        await usersApi.logout(user);
      }
      return { success: true };
    } catch (e: any) {
      setMessage({
        title: 'Remote session logout failure',
        description: e.message
      });
      return { success: false, message: e.message };
    }
  };

  const checkForUpdate = async (): Promise<void> => {
    set(showUpdatePopup, await checkForUpdates());
  };

  const changePassword = async ({
    currentPassword,
    newPassword
  }: ChangePasswordPayload): Promise<ActionStatus> => {
    try {
      const success = await usersApi.changeUserPassword(
        get(username),
        currentPassword,
        newPassword
      );
      setMessage({
        description: t('actions.session.password_change.success').toString(),
        success: true
      });

      if (success && isPackaged) {
        clearPassword()
          .then(() => logger.info('clear complete'))
          .catch(e => logger.error(e));
      }

      return {
        success
      };
    } catch (e: any) {
      setMessage({
        description: t('actions.session.password_change.error', {
          message: e.message
        }).toString()
      });
      return {
        success: false,
        message: e.message
      };
    }
  };

  const { lastLanguage } = useLastLanguage();
  const { language } = storeToRefs(useFrontendSettingsStore());

  const adaptiveLanguage: ComputedRef<SupportedLanguage> = computed(() => {
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
    checkForAssetUpdate
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionStore, import.meta.hot));
}
