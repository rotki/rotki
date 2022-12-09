import { useBackendManagement } from '@/composables/backend';
import { useAppNavigation } from '@/composables/navigation';
import { usePremiumReminder } from '@/composables/premium';
import { useSessionStore } from '@/store/session';
import { useSessionAuthStore } from '@/store/session/auth';
import {
  type CreateAccountPayload,
  type LoginCredentials
} from '@/types/login';
import { setLastLogin } from '@/utils/account-management';

export const useAccountManagement = () => {
  const loading = ref(false);
  const error = ref<string>('');
  const errors = ref<string[]>([]);

  const { tc } = useI18n();
  const { showGetPremiumButton, showPremiumDialog } = usePremiumReminder();
  const { navigateToDashboard } = useAppNavigation();
  const { createAccount, login } = useSessionStore();
  const authStore = useSessionAuthStore();
  const { logged } = storeToRefs(authStore);
  const { updateLoginStatus } = authStore;

  const createNewAccount = async (payload: CreateAccountPayload) => {
    set(loading, true);
    set(error, '');
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
    const result = await login({
      username,
      password,
      syncApproval
    });

    if (!result.success) {
      set(errors, [result.message]);
    }
    set(loading, false);
    updateLoginStatus();
    if (get(logged)) {
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
  const { logged } = storeToRefs(useSessionAuthStore());
  const { resetSessionBackend } = useBackendManagement();
  const { showGetPremiumButton, showPremiumDialog } = usePremiumReminder();

  onMounted(async () => {
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
