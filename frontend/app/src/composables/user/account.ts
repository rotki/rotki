import { wait } from '@shared/utils';
import { setLastLogin } from '@/utils/account-management';
import { useMainStore } from '@/store/main';
import { useSessionAuthStore } from '@/store/session/auth';
import { useWebsocketStore } from '@/store/websocket';
import { useSessionStore } from '@/store/session';
import { useBackendManagement } from '@/composables/backend';
import { usePremiumReminder } from '@/composables/premium';
import { useAppNavigation } from '@/composables/navigation';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import type { CreateAccountPayload, LoginCredentials } from '@/types/login';
import type { Ref } from 'vue';

interface UseAccountManagementReturn {
  loading: Ref<boolean>;
  error: Ref<string>;
  errors: Ref<string[]>;
  createNewAccount: (payload: CreateAccountPayload) => Promise<void>;
  userLogin: ({ password, resumeFromBackup, syncApproval, username }: LoginCredentials) => Promise<void>;
}

export function useAccountManagement(): UseAccountManagementReturn {
  const { t } = useI18n();
  const loading = ref<boolean>(false);
  const error = ref<string>('');
  const errors = ref<string[]>([]);

  const { showGetPremiumButton } = usePremiumReminder();
  const { navigateToDashboard } = useAppNavigation();
  const sessionStore = useSessionStore();
  const { checkForAssetUpdate } = storeToRefs(sessionStore);
  const { createAccount, login } = sessionStore;
  const { connect } = useWebsocketStore();
  const authStore = useSessionAuthStore();
  const { canRequestData, logged, upgradeVisible } = storeToRefs(authStore);
  const { clearUpgradeMessages } = authStore;
  const { isDevelop } = storeToRefs(useMainStore());
  const loggedUserIdentifier = useLoggedUserIdentifier();

  const createNewAccount = async (payload: CreateAccountPayload): Promise<void> => {
    set(loading, true);
    set(error, '');
    const username = payload.credentials.username;
    const userIdentifier = `${username}${get(isDevelop) ? '.dev' : ''}`;
    set(loggedUserIdentifier, userIdentifier);

    await connect();
    const start = Date.now();
    const result = await createAccount(payload);
    const duration = (Date.now() - start) / 1000;

    if (result.success) {
      if (get(upgradeVisible) && duration < 10)
        await wait(3000);

      if (get(logged)) {
        clearUpgradeMessages();
        showGetPremiumButton();
        set(canRequestData, true);
        await navigateToDashboard();
      }
    }
    else {
      set(error, result.message ?? t('account_management.creation.error'));
    }

    set(loading, false);
  };

  const userLogin = async ({ password, resumeFromBackup, syncApproval, username }: LoginCredentials): Promise<void> => {
    set(loading, true);
    const userIdentifier = `${username}${get(isDevelop) ? '.dev' : ''}`;
    set(loggedUserIdentifier, userIdentifier);
    await connect();

    const result = await login({
      password,
      resumeFromBackup: resumeFromBackup || false,
      syncApproval: syncApproval || 'unknown',
      username,
    });

    if (!result.success && result.message)
      set(errors, [result.message]);

    set(loading, false);
    if (get(logged)) {
      clearUpgradeMessages();
      setLastLogin(username);
      showGetPremiumButton();
      set(checkForAssetUpdate, true);
    }
  };

  return {
    createNewAccount,
    error,
    errors,
    loading,
    userLogin,
  };
}

interface UseAutoLoginReturn { autolog: Ref<boolean> }

export function useAutoLogin(): UseAutoLoginReturn {
  const autolog = ref<boolean>(false);

  const sessionStore = useSessionStore();
  const { checkForAssetUpdate } = storeToRefs(sessionStore);
  const { login } = sessionStore;
  const { connected } = storeToRefs(useMainStore());
  const { canRequestData, logged } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton } = usePremiumReminder();

  watch(connected, async (connected) => {
    if (!connected)
      return;

    await resetSessionBackend();

    set(autolog, true);

    await login({ password: '', username: '' });

    if (get(logged)) {
      showGetPremiumButton();
      set(checkForAssetUpdate, true);
      set(canRequestData, true);
    }

    set(autolog, false);
  });

  return {
    autolog,
  };
}

export const useRestartingStatus = createSharedComposable(() => {
  const restarting = ref<boolean>(false);

  return { restarting };
});
