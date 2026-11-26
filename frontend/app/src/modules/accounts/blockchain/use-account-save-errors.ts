import { set } from '@vueuse/shared';
import { readonly, type Ref, ref, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';

export interface UseAccountSaveErrorsReturn {
  modelErrorMessages: Ref<ValidationErrors>;
  saveError: Readonly<Ref<string>>;
  saveErrorIsPremium: Readonly<Ref<boolean>>;
  /** Shows a failed save: field errors go to the form, anything else above it. */
  handleErrors: (error: unknown, props?: Record<string, any>) => void;
  /** Shows a validator save that threw. */
  handleValidatorError: (error: unknown) => void;
  /** Shows a validator save the backend refused. */
  showValidatorRefusal: (message: ValidationErrors | string) => void;
  resetSaveError: () => void;
}

/**
 * Holds the errors an account form shows after a save, and turns a failed save into them.
 */
export function useAccountSaveErrors(): UseAccountSaveErrorsReturn {
  const modelErrorMessages = ref<ValidationErrors>({});
  const saveError = shallowRef<string>('');
  const saveErrorIsPremium = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  function handleErrors(error: unknown, props: Record<string, any> = {}): void {
    logger.error(error);
    let errors: ValidationErrors | string = getErrorMessage(error);

    if (!(error instanceof ApiValidationError)) {
      const parsed = new ApiValidationError(errors);
      if (Object.keys(parsed.errors).length > 0)
        error = parsed;
    }

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(props);

    if (typeof errors === 'string')
      set(saveError, errors);
    else
      set(modelErrorMessages, errors);
  }

  /** Field errors go to the form; a message goes above it, with a hint when credentials are missing. */
  function showValidatorRefusal(message: ValidationErrors | string): void {
    if (typeof message !== 'string') {
      set(modelErrorMessages, message);
      return;
    }
    set(saveErrorIsPremium, message.includes('limit exceeded'));
    set(saveError, message.includes('failed due to missing API key')
      ? t('account_form.error.validator_needs_credentials')
      : message);
  }

  function handleValidatorError(error: unknown): void {
    logger.error(error);
    if (error instanceof ApiValidationError) {
      const validation = error.getValidationErrors({
        ownershipPercentage: '',
        publicKey: '',
        validatorIndex: '',
      });
      if (typeof validation === 'string')
        set(saveError, validation);
      else
        set(modelErrorMessages, validation);
    }
    else {
      set(saveError, getErrorMessage(error));
    }
  }

  function resetSaveError(): void {
    set(saveError, '');
    set(saveErrorIsPremium, false);
  }

  return {
    handleErrors,
    handleValidatorError,
    modelErrorMessages,
    resetSaveError,
    saveError: readonly(saveError),
    saveErrorIsPremium: readonly(saveErrorIsPremium),
    showValidatorRefusal,
  };
}
