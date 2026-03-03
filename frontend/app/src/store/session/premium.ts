import type { ActionStatus } from '@/types/action';
import type { PremiumCapabilities, PremiumCredentialsPayload } from '@/types/session';
import { usePremiumCredentialsApi } from '@/composables/api/session/premium-credentials';
import { useSessionAuthStore } from '@/store/session/auth';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { getErrorMessage } from '@/utils/error-handling';
import { logger } from '@/utils/logging';

export const usePremiumStore = defineStore('session/premium', () => {
  const premium = ref<boolean>(false);
  const premiumSync = ref<boolean>(false);
  const capabilities = ref<PremiumCapabilities>();

  const api = usePremiumCredentialsApi();

  const setup = async ({
    apiKey,
    apiSecret,
    username,
  }: PremiumCredentialsPayload): Promise<ActionStatus<string | ValidationErrors>> => {
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
  };

  const deletePremium = async (): Promise<ActionStatus> => {
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
  };

  const { logged } = storeToRefs(useSessionAuthStore());

  watchImmediate([premium, logged], async ([, isLogged]) => {
    if (!isLogged) {
      set(capabilities, undefined);
      return;
    }

    try {
      const result = await api.getPremiumCapabilities();
      set(capabilities, result);
    }
    catch (error: unknown) {
      logger.error('Failed to fetch premium capabilities:', error);
    }
  });

  return {
    capabilities,
    deletePremium,
    premium,
    premiumSync,
    setup,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(usePremiumStore, import.meta.hot));
