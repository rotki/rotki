import { useSessionStore } from '@/store/session';
import { useSessionAuthStore } from '@/store/session/auth';
import {
  type CreateAccountPayload,
  type LoginCredentials
} from '@/types/login';
import { setLastLogin } from '@/utils/account-management';
import { useWebsocketStore } from '@/store/websocket';
import { useMainStore } from '@/store/main';
import { useNotificationsStore } from '@/store/notifications';
import { useAccountMigrationStore } from '@/store/blockchain/accounts/migrate';

export const useAccountManagement = () => {
  const loading = ref(false);
  const error = ref<string>('');
  const errors = ref<string[]>([]);

  const { tc } = useI18n();
  const { showGetPremiumButton, showPremiumDialog } = usePremiumReminder();
  const { navigateToDashboard } = useAppNavigation();
  const { createAccount, login } = useSessionStore();
  const { connect } = useWebsocketStore();
  const authStore = useSessionAuthStore();
  const { logged } = storeToRefs(authStore);
  const { updateDbUpgradeStatus, updateDataMigrationStatus } = authStore;
  const { upgradeMigratedAddresses } = useAccountMigrationStore();
  const { restorePending, initPending } = useNotificationsStore();

  const createNewAccount = async (payload: CreateAccountPayload) => {
    set(loading, true);
    set(error, '');
    initPending(payload.credentials.username);
    await connect();
    const result = await createAccount(payload);
    set(loading, false);

    if (result.success) {
      if (get(logged)) {
        showGetPremiumButton();
        await navigateToDashboard();
      }
    } else {
      set(error, result.message ?? tc('account_management.creation.error'));
    }
  };

  const userLogin = async ({
    username,
    password,
    syncApproval
  }: LoginCredentials) => {
    set(loading, true);
    initPending(username);
    await connect();
    const result = await login({
      username,
      password,
      syncApproval
    });

    if (!result.success) {
      set(errors, [result.message]);
    }
    set(loading, false);
    updateDbUpgradeStatus();
    updateDataMigrationStatus();
    upgradeMigratedAddresses();
    if (get(logged)) {
      restorePending();
      setLastLogin(username);
      showGetPremiumButton();
      await showPremiumDialog();
    }
  };

  return {
    loading,
    error,
    errors,
    createNewAccount,
    userLogin
  };
};

export const useAutoLogin = () => {
  const autolog = ref(false);

  const { login } = useSessionStore();
  const { connected } = storeToRefs(useMainStore());
  const { logged } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton, showPremiumDialog } = usePremiumReminder();

  watch(connected, async connected => {
    if (!connected) {
      return;
    }

    await resetSessionBackend();

    set(autolog, true);

    await login({ username: '', password: '' });

    if (get(logged)) {
      await showPremiumDialog();
      showGetPremiumButton();
    }

    set(autolog, false);
  });

  return {
    autolog
  };
};
