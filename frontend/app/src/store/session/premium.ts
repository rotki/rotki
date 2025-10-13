import type { ActionStatus } from '@/types/action';
import type { PremiumCapabilities, PremiumCredentialsPayload } from '@/types/session';
import { usePremiumCredentialsApi } from '@/composables/api/session/premium-credentials';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
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
    catch (error: any) {
      let errors: string | ValidationErrors = error.message;
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
    catch (error: any) {
      return {
        message: error.message,
        success: false,
      };
    }
  };

  watch(premium, async (isPremium: boolean, wasPremium: boolean) => {
    if (isPremium && !wasPremium) {
      try {
        const result = await api.getPremiumCapabilities();
        set(capabilities, result);
      }
      catch (error: any) {
        logger.error('Failed to fetch premium capabilities:', error);
      }
    }
    else if (wasPremium && !isPremium) {
      set(capabilities, undefined);
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
