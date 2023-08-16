import {
  type CreateAccountPayload,
  type LoginCredentials
} from '@/types/login';

export const useAccountManagement = () => {
  const { t } = useI18n();
  const loading: Ref<boolean> = ref(false);
  const error: Ref<string> = ref('');
  const errors: Ref<string[]> = ref([]);

  const { showGetPremiumButton } = usePremiumReminder();
  const { navigateToDashboard } = useAppNavigation();
  const sessionStore = useSessionStore();
  const { checkForAssetUpdate } = storeToRefs(sessionStore);
  const { createAccount, login } = sessionStore;
  const { connect } = useWebsocketStore();
  const authStore = useSessionAuthStore();
  const { logged, canRequestData, upgradeVisible } = storeToRefs(authStore);
  const { clearUpgradeMessages } = authStore;
  const { setupCache } = useAccountMigrationStore();
  const { initTokens } = useNewlyDetectedTokens();
  const { isDevelop } = storeToRefs(useMainStore());

  const createNewAccount = async (payload: CreateAccountPayload) => {
    set(loading, true);
    set(error, '');
    const username = payload.credentials.username;
    const userIdentifier = `${username}${get(isDevelop) ? '.dev' : ''}`;
    setupCache(userIdentifier);
    initTokens(userIdentifier);
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
    syncApproval,
    resumeFromBackup
  }: LoginCredentials): Promise<void> => {
    set(loading, true);
    const userIdentifier = `${username}${get(isDevelop) ? '.dev' : ''}`;
    setupCache(userIdentifier);
    initTokens(userIdentifier);
    await connect();

    const result = await login({
      username,
      password,
      syncApproval: syncApproval || 'unknown',
      resumeFromBackup: resumeFromBackup || false
    });

    if (!result.success && result.message) {
      set(errors, [result.message]);
    }
    set(loading, false);
    if (get(logged)) {
      clearUpgradeMessages();
      setLastLogin(username);
      showGetPremiumButton();
      set(checkForAssetUpdate, true);
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
  const autolog: Ref<boolean> = ref(false);

  const sessionStore = useSessionStore();
  const { checkForAssetUpdate } = storeToRefs(sessionStore);
  const { login } = sessionStore;
  const { connected } = storeToRefs(useMainStore());
  const { logged, canRequestData } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton } = usePremiumReminder();

  watch(connected, async connected => {
    if (!connected) {
      return;
    }

    await resetSessionBackend();

    set(autolog, true);

    await login({ username: '', password: '' });

    if (get(logged)) {
      showGetPremiumButton();
      set(checkForAssetUpdate, true);
      set(canRequestData, true);
    }

    set(autolog, false);
  });

  return {
    autolog
  };
};
