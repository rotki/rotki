import { type Ref } from 'vue';
import { useSessionStore } from '@/store/session';
import { useSessionAuthStore } from '@/store/session/auth';
import {
  type CreateAccountPayload,
  type LoginCredentials
} from '@/types/login';
import { setLastLogin } from '@/utils/account-management';
import { useWebsocketStore } from '@/store/websocket';
import { useMainStore } from '@/store/main';
import { useAccountMigrationStore } from '@/store/blockchain/accounts/migrate';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';

export const useAccountManagement = () => {
  const loading: Ref<boolean> = ref(false);
  const error: Ref<string> = ref('');
  const errors: Ref<string[]> = ref([]);

  const { tc } = useI18n();
  const { showGetPremiumButton, showPremiumDialog } = usePremiumReminder();
  const { navigateToDashboard } = useAppNavigation();
  const { createAccount, login } = useSessionStore();
  const { connect } = useWebsocketStore();
  const authStore = useSessionAuthStore();
  const { logged, canRequestData } = storeToRefs(authStore);
  const { updateDbUpgradeStatus, updateDataMigrationStatus } = authStore;
  const { setupCache } = useAccountMigrationStore();
  const { initTokens } = useNewlyDetectedTokens();

  const createNewAccount = async (payload: CreateAccountPayload) => {
    set(loading, true);
    set(error, '');
    setupCache(payload.credentials.username);
    initTokens(payload.credentials.username);
    await connect();
    const result = await createAccount(payload);
    set(loading, false);

    if (result.success) {
      if (get(logged)) {
        showGetPremiumButton();
        set(canRequestData, true);
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
  }: LoginCredentials): Promise<boolean> => {
    set(loading, true);
    setupCache(username);
    initTokens(username);
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
    if (get(logged)) {
      setLastLogin(username);
      showGetPremiumButton();
      return showPremiumDialog();
    }
    return false;
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
  const autolog: Ref<boolean> = ref(false);

  const { login } = useSessionStore();
  const { connected } = storeToRefs(useMainStore());
  const { logged, canRequestData } = storeToRefs(useSessionAuthStore());
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
      set(canRequestData, true);
    }

    set(autolog, false);
  });

  return {
    autolog
  };
};
