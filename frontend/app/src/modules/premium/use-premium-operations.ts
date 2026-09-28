import type { ActionStatus } from '@/modules/core/common/action';
import type { PremiumCredentialsPayload } from '@/modules/session/types';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useFetchPremiumCapabilities } from '@/modules/premium/use-fetch-premium-capabilities';
import { usePremiumCredentialsApi } from '@/modules/premium/use-premium-credentials-api';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

interface UsePremiumOperationsReturn {
  deletePremium: () => Promise<ActionStatus>;
  setup: (payload: PremiumCredentialsPayload) => Promise<ActionStatus<string | ValidationErrors>>;
}

/**
 * Saving and removing the premium key.
 *
 * @remarks
 * Either one settles the action center's premium row: a saved key is verified when it is saved, and
 * a removed key is no longer checked.
 */
export function usePremiumOperations(): UsePremiumOperationsReturn {
  const api = usePremiumCredentialsApi();
  const { capabilities, premium } = storeToRefs(usePremiumStore());
  const { fetchCapabilities } = useFetchPremiumCapabilities();
  const { clear } = useRaisedConditionsStore();

  function clearInactiveRow(): void {
    clear(({ kind }) => kind === RaisedConditionKind.PREMIUM_INACTIVE);
  }

  async function setup({
    apiKey,
    apiSecret,
    username,
  }: PremiumCredentialsPayload): Promise<ActionStatus<string | ValidationErrors>> {
    try {
      const success = await api.setPremiumCredentials(username, apiKey, apiSecret);

      if (success) {
        set(premium, true);
        clearInactiveRow();
        await fetchCapabilities();
      }

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
        clearInactiveRow();
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
