import type { Ref } from 'vue';
import type { CreateAccountPayload, LoginCredentials } from '@/modules/account/login';
import { wait } from '@shared/utils';
import dayjs from 'dayjs';
import { useBackendManagement } from '@/composables/backend';
import { useAppNavigation } from '@/composables/navigation';
import { usePremiumHelper } from '@/composables/premium';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { lastLogin } from '@/modules/account/account-management';
import { useLogin } from '@/modules/account/use-login';
import { usePasswordConfirmation } from '@/modules/account/use-password-confirmation';
import { useWebsocketConnection } from '@/modules/app/use-websocket-connection';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useMainStore } from '@/store/main';
import { useSessionAuthStore } from '@/store/session/auth';

interface UseAccountManagementReturn {
  loading: Readonly<Ref<boolean>>;
  error: Readonly<Ref<string>>;
  errors: Ref<string[]>;
  createNewAccount: (payload: CreateAccountPayload) => Promise<void>;
  userLogin: ({ password, resumeFromBackup, syncApproval, username }: LoginCredentials) => Promise<void>;
  clearErrors: () => void;
}

export function useAccountManagement(): UseAccountManagementReturn {
  const { t } = useI18n({ useScope: 'global' });
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>('');
  const errors = ref<string[]>([]);

  const { showGetPremiumButton } = usePremiumHelper();
  const { navigateToDashboard } = useAppNavigation();
  const { createAccount, login } = useLogin();
  const { connect } = useWebsocketConnection();
  const authStore = useSessionAuthStore();
  const { canRequestData, logged, upgradeVisible } = storeToRefs(authStore);
  const { clearUpgradeMessages } = authStore;
  const { isDevelop } = storeToRefs(useMainStore());
  const loggedUserIdentifier = useLoggedUserIdentifier();
  const { disconnect: disconnectWallet } = useWalletStore();
  const { fetchTransactionStatusSummary } = useHistoryDataFetching();
  const { updateFrontendSetting } = useSettingsOperations();

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
        set(lastLogin, username);
        showGetPremiumButton();
        set(canRequestData, true);
        await fetchTransactionStatusSummary();
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
      set(lastLogin, username);
      // Manual login counts as password confirmation
      await updateFrontendSetting({ lastPasswordConfirmed: dayjs().unix() });
      showGetPremiumButton();
      await fetchTransactionStatusSummary();
      await disconnectWallet();
    }
  };

  function clearErrors(): void {
    set(errors, []);
  }

  return {
    createNewAccount,
    clearErrors,
    error: readonly(error),
    errors,
    loading: readonly(loading),
    userLogin,
  };
}

interface UseAutoLoginReturn {
  autolog: Ref<boolean>;
  needsPasswordConfirmation: Ref<boolean>;
  confirmPassword: (password: string) => Promise<boolean>;
  checkIfPasswordConfirmationNeeded: (usernameToCheck: string) => Promise<void>;
  username: Ref<string>;
}

export function useAutoLogin(): UseAutoLoginReturn {
  const autolog = shallowRef<boolean>(false);
  const isAutoLoginFlow = shallowRef<boolean>(false);

  const { login } = useLogin();
  const { connected } = storeToRefs(useMainStore());
  const authStore = useSessionAuthStore();
  const { canRequestData, logged, username } = storeToRefs(authStore);
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton } = usePremiumHelper();
  const { checkIfPasswordConfirmationNeeded, confirmPassword, needsPasswordConfirmation } = usePasswordConfirmation();

  watch(connected, async (connected) => {
    if (!connected)
      return;

    await resetSessionBackend();

    const savedUsername = get(lastLogin);
    if (!savedUsername) {
      // No saved credentials, can't auto-login
      return;
    }

    // Mark that we're starting an auto-login flow
    set(isAutoLoginFlow, true);
    set(autolog, true);

    // Try to login with empty password (auto-login)
    await login({ password: '', username: '' });

    set(autolog, false);
  });

  // Watch for successful auto-login and check if password confirmation is needed
  watch(logged, async (isLogged) => {
    // Only proceed if this is an auto-login flow
    if (!get(isAutoLoginFlow))
      return;

    if (!isLogged)
      return;

    // Reset the auto-login flow flag
    set(isAutoLoginFlow, false);

    const savedUsername = get(lastLogin);
    if (!savedUsername)
      return;

    // Check if password confirmation is needed AFTER successful auto-login
    await checkIfPasswordConfirmationNeeded(savedUsername);

    showGetPremiumButton();
    set(canRequestData, true);
  });

  return {
    autolog,
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation,
    username,
  };
}

export const useRestartingStatus = createSharedComposable(() => {
  const restarting = ref<boolean>(false);

  return { restarting };
});
