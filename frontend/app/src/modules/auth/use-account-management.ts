import type { ComputedRef } from 'vue';
import type { CreateAccountPayload, LoginCredentials } from '@/modules/auth/login';
import { UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';
import { useUnlockFlowController } from '@/modules/auth/unlock-flow/use-unlock-flow-controller';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useMainStore } from '@/modules/core/common/use-main-store';

interface UseAccountManagementReturn {
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  errors: ComputedRef<string[]>;
  createNewAccount: (payload: CreateAccountPayload) => Promise<void>;
  userLogin: (credentials: LoginCredentials) => Promise<void>;
  clearErrors: () => void;
}

/**
 * Page-facing facade over the shared unlock-flow controller. Both pages drive the same
 * flow machine; this only adapts the controller to the small surface the login/create
 * pages already consume. `error`/`errors`/`loading` are pure projections of the flow
 * state, and the post-unlock side-effects + navigation live in the controller, not here.
 */
export function useAccountManagement(): UseAccountManagementReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { isDevelop } = storeToRefs(useMainStore());
  const loggedUserIdentifier = useLoggedUserIdentifier();
  const controller = useUnlockFlowController();

  // Single-string error for the create wizard (the login form uses the `errors` array).
  const error = computed<string>(() => {
    if (get(controller.state).kind !== UnlockPhase.error)
      return '';
    return get(controller.errors)[0] ?? t('account_management.creation.error');
  });

  function trackIdentifier(username: string): void {
    set(loggedUserIdentifier, `${username}${get(isDevelop) ? '.dev' : ''}`);
  }

  const createNewAccount = async (payload: CreateAccountPayload): Promise<void> => {
    trackIdentifier(payload.credentials.username);
    await controller.startCreate(payload);
  };

  const userLogin = async (credentials: LoginCredentials): Promise<void> => {
    trackIdentifier(credentials.username);
    await controller.startLogin({
      ...credentials,
      resumeFromBackup: credentials.resumeFromBackup ?? false,
      syncApproval: credentials.syncApproval ?? 'unknown',
    });
  };

  return {
    clearErrors: controller.reset,
    createNewAccount,
    error,
    errors: controller.errors,
    loading: controller.loading,
    userLogin,
  };
}
