import { type Ref } from 'vue';
import {
  type CreateAccountPayload,
  type LoginCredentials
} from '@/types/login';

export const useAccountManagement = () => {
  const { t } = useI18n();
  const loading: Ref<boolean> = ref(false);
  const error: Ref<string> = ref('');
  const errors: Ref<string[]> = ref([]);

  const { showGetPremiumButton, showPremiumDialog } = usePremiumReminder();
  const { navigateToDashboard } = useAppNavigation();
  const { createAccount, login } = useSessionStore();
  const { connect } = useWebsocketStore();
  const authStore = useSessionAuthStore();
  const { logged, canRequestData, upgradeVisible } = storeToRefs(authStore);
  const { clearUpgradeMessages } = authStore;
  const { setupCache } = useAccountMigrationStore();
  const { initTokens } = useNewlyDetectedTokens();

  const createNewAccount = async (payload: CreateAccountPayload) => {
    set(loading, true);
    set(error, '');
    setupCache(payload.credentials.username);
    initTokens(payload.credentials.username);
    await connect();
    const start = Date.now();
    const result = await createAccount(payload);
    const duration = (Date.now() - start) / 1000;
    set(loading, false);

    if (result.success) {
      if (get(upgradeVisible) && duration < 10) {
        await wait(3000);
      }
      if (get(logged)) {
        clearUpgradeMessages();
        showGetPremiumButton();
        set(canRequestData, true);
        await navigateToDashboard();
      }
    } else {
      set(error, result.message ?? t('account_management.creation.error'));
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
    if (get(logged)) {
      clearUpgradeMessages();
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
