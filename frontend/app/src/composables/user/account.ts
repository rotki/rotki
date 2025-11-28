import type { Ref } from 'vue';
import type { CreateAccountPayload, LoginCredentials } from '@/types/login';
import { wait } from '@shared/utils';
import dayjs from 'dayjs';
import { useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/composables/electron-interop';
import { useAppNavigation } from '@/composables/navigation';
import { usePremiumHelper } from '@/composables/premium';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useLogin } from '@/modules/account/use-login';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useHistoryStore } from '@/store/history';
import { useMainStore } from '@/store/main';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useWebsocketStore } from '@/store/websocket';
import { lastLogin } from '@/utils/account-management';

interface UseAccountManagementReturn {
  loading: Ref<boolean>;
  error: Ref<string>;
  errors: Ref<string[]>;
  createNewAccount: (payload: CreateAccountPayload) => Promise<void>;
  userLogin: ({ password, resumeFromBackup, syncApproval, username }: LoginCredentials) => Promise<void>;
}

export function useAccountManagement(): UseAccountManagementReturn {
  const { t } = useI18n({ useScope: 'global' });
  const loading = ref<boolean>(false);
  const error = ref<string>('');
  const errors = ref<string[]>([]);

  const { showGetPremiumButton } = usePremiumHelper();
  const { navigateToDashboard } = useAppNavigation();
  const { createAccount, login } = useLogin();
  const { connect } = useWebsocketStore();
  const authStore = useSessionAuthStore();
  const { canRequestData, checkForAssetUpdate, logged, upgradeVisible } = storeToRefs(authStore);
  const { clearUpgradeMessages } = authStore;
  const { isDevelop } = storeToRefs(useMainStore());
  const loggedUserIdentifier = useLoggedUserIdentifier();
  const { disconnect: disconnectWallet } = useWalletStore();
  const { fetchTransactionStatusSummary } = useHistoryStore();
  const { updateSetting } = useFrontendSettingsStore();

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
      await updateSetting({ lastPasswordConfirmed: dayjs().unix() });
      showGetPremiumButton();
      set(checkForAssetUpdate, true);
      await fetchTransactionStatusSummary();
      await disconnectWallet();
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

interface UseAutoLoginReturn {
  autolog: Ref<boolean>;
  needsPasswordConfirmation: Ref<boolean>;
  confirmPassword: (password: string) => Promise<boolean>;
  checkIfPasswordConfirmationNeeded: (usernameToCheck: string) => Promise<void>;
  username: Ref<string>;
}

export function useAutoLogin(): UseAutoLoginReturn {
  const autolog = ref<boolean>(false);
  const isAutoLoginFlow = ref<boolean>(false);

  const { login } = useLogin();
  const { connected } = storeToRefs(useMainStore());
  const authStore = useSessionAuthStore();
  const { canRequestData, checkForAssetUpdate, logged, needsPasswordConfirmation, username } = storeToRefs(authStore);
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton } = usePremiumHelper();
  const { getPassword } = useInterop();
  const frontendSettingsStore = useFrontendSettingsStore();
  const { updateSetting } = frontendSettingsStore;
  const { enablePasswordConfirmation, lastPasswordConfirmed, passwordConfirmationInterval } = storeToRefs(frontendSettingsStore);

  const checkIfPasswordConfirmationNeeded = async (usernameToCheck: string): Promise<void> => {
    if (!get(enablePasswordConfirmation))
      return;

    // Check if user has stored password (remember password enabled)
    const storedPassword = await getPassword(usernameToCheck);
    if (!storedPassword)
      return;

    const lastConfirmed = get(lastPasswordConfirmed);

    // If lastPasswordConfirmed is 0, this is the first time using the feature
    // (new account or existing user with new feature) - initialize the timer
    const now = dayjs().unix();

    if (lastConfirmed === 0) {
      await updateSetting({ lastPasswordConfirmed: now });
      return;
    }

    if ((now - lastConfirmed) > get(passwordConfirmationInterval))
      set(needsPasswordConfirmation, true);
  };

  const confirmPassword = async (password: string): Promise<boolean> => {
    // Verify password by comparing with stored password
    const storedPassword = await getPassword(get(username));

    if (password === storedPassword) {
      // Password correct - close dialog and update timestamp
      set(needsPasswordConfirmation, false);
      const now = dayjs().unix();
      await updateSetting({ lastPasswordConfirmed: now });

      return true;
    }

    // Password incorrect - dialog stays open
    return false;
  };

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
    set(checkForAssetUpdate, true);
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
