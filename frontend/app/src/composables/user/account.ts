import type { Ref } from 'vue';
import type { CreateAccountPayload, LoginCredentials } from '@/types/login';
import { wait } from '@shared/utils';
import { useBackendManagement } from '@/composables/backend';
import { useAppNavigation } from '@/composables/navigation';
import { usePremiumHelper } from '@/composables/premium';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useLogin } from '@/modules/account/use-login';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useHistoryStore } from '@/store/history';
import { useMainStore } from '@/store/main';
import { useSessionAuthStore } from '@/store/session/auth';
import { useWebsocketStore } from '@/store/websocket';
import { setLastLogin } from '@/utils/account-management';

interface UseAccountManagementReturn {
  loading: Ref<boolean>;
  error: Ref<string>;
  errors: Ref<string[]>;
  createNewAccount: (payload: CreateAccountPayload) => Promise<void>;
  userLogin: (credentials: LoginCredentials) => Promise<void>;
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
        await fetchTransactionStatusSummary();
        await navigateToDashboard();
      }
    }
    else {
      set(error, result.message ?? t('account_management.creation.error'));
    }

    set(loading, false);
  };

  const userLogin = async (credentials: LoginCredentials): Promise<void> => {
    set(loading, true);
    const { username, password, resumeFromBackup, syncApproval, auto_login, is_confirmation } = credentials;
    const userIdentifier = `${username}${get(isDevelop) ? '.dev' : ''}`;
    set(loggedUserIdentifier, userIdentifier);
    await connect();

    const result = await login({
      password,
      resumeFromBackup: resumeFromBackup || false,
      syncApproval: syncApproval || 'unknown',
      username,
      auto_login: auto_login || false,
      is_confirmation: is_confirmation || false,
    });

    // Handle requires_confirmation separately - it's not an error, just a state
    if (!result.success && result.message) {
      if (result.message.startsWith('requires_confirmation'))
        set(errors, [result.message]); // This will be handled silently by LoginForm watcher
      else
        set(errors, [result.message]); // Display other errors normally
    }

    set(loading, false);
    if (get(logged)) {
      clearUpgradeMessages();
      setLastLogin(username);
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

interface UseAutoLoginReturn { autolog: Ref<boolean> }

export function useAutoLogin(): UseAutoLoginReturn {
  const autolog = ref<boolean>(false);

  const { login } = useLogin();
  const { connected } = storeToRefs(useMainStore());
  const { canRequestData, checkForAssetUpdate, logged } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton } = usePremiumHelper();

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
