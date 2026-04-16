import type { ActionStatus } from '@/modules/common/action';
import type { PremiumCredentialsPayload } from '@/modules/session/types';
import { usePremiumCredentialsApi } from '@/composables/api/session/premium-credentials';
import { ApiValidationError, type ValidationErrors } from '@/modules/api/types/errors';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

interface UsePremiumOperationsReturn {
  deletePremium: () => Promise<ActionStatus>;
  setup: (payload: PremiumCredentialsPayload) => Promise<ActionStatus<string | ValidationErrors>>;
}

export function usePremiumOperations(): UsePremiumOperationsReturn {
  const api = usePremiumCredentialsApi();
  const { capabilities, premium } = storeToRefs(usePremiumStore());

  async function setup({
    apiKey,
    apiSecret,
    username,
  }: PremiumCredentialsPayload): Promise<ActionStatus<string | ValidationErrors>> {
    try {
      const success = await api.setPremiumCredentials(username, apiKey, apiSecret);

      if (success)
        set(premium, true);

      return { success };
    }
    catch (error: unknown) {
      let errors: string | ValidationErrors = getErrorMessage(error);
      if (error instanceof ApiValidationError) {
        errors = error.getValidationErrors({
          apiKey,
          apiSecret,
        });
      }

      return {
        message: errors,
        success: false,
      };
    }
  }

  async function deletePremium(): Promise<ActionStatus> {
    try {
      const success = await api.deletePremiumCredentials();
      if (success) {
        set(premium, false);
        set(capabilities, undefined);
      }

      return { success };
    }
    catch (error: unknown) {
      return {
        message: getErrorMessage(error),
        success: false,
      };
    }
  }

  return {
    deletePremium,
    setup,
  };
}
