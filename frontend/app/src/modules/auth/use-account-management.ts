import type { Ref } from 'vue';
import type { CreateAccountPayload, LoginCredentials } from '@/modules/auth/login';
import { wait } from '@shared/utils';
import dayjs from 'dayjs';
import { lastLogin } from '@/modules/auth/account-management';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useLogin } from '@/modules/auth/use-login';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useWebsocketConnection } from '@/modules/shell/app/use-websocket-connection';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

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
