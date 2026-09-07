import type { SupportedAsset } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { omit } from 'es-toolkit';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';

/**
 * The error keys the dialog reports as a message rather than on a field.
 *
 * @remarks
 * `underlyingTokens` has no single input to attach to. Marshmallow reports whole-payload failures
 * under `_schema`, which reaches here as `Schema`: `ApiValidationError` runs the payload through
 * `camelCaseTransformer`, and both spellings normalise to that one.
 */
const MESSAGE_ONLY_KEYS = ['underlyingTokens', 'Schema'] as const;

interface ManagedAssetFormHandle {
  /** Runs the form's own validation. */
  validate: () => boolean;
  /** Writes the asset and resolves its identifier, or nothing when the write failed. */
  saveAsset: () => Promise<string | undefined>;
  /** Uploads the pending icon for the saved asset. */
  saveIcon: (identifier: string) => void;
}

interface UseManagedAssetFormDialogOptions {
  /** Whether the dialog is editing rather than creating; it only changes the wording. */
  editMode: MaybeRefOrGetter<boolean>;
  /** The asset being edited, cleared once the write lands. */
  modelValue: Ref<SupportedAsset | undefined>;
  /** Called after a successful write, so the caller can refresh its list. */
  onSaved: () => void;
  /** The form component, which owns validation and the write itself. */
  form: MaybeRefOrGetter<ManagedAssetFormHandle | null | undefined>;
}

interface UseManagedAssetFormDialogReturn {
  /** The dialog's title, which differs between adding and editing. */
  dialogTitle: ComputedRef<string>;
  /** Field errors returned by the server. */
  modelErrorMessages: Ref<ValidationErrors>;
  /** Whether a write is in flight. */
  loading: Readonly<Ref<boolean>>;
  /**
   * Validates and writes the asset.
   *
   * @returns whether it landed; `false` leaves the dialog open with the reason shown
   */
  save: () => Promise<boolean>;
}

/**
 * Drives the managed asset dialog: validating, writing through the form, and splitting a failure
 * between the fields it belongs to and a message for the rest.
 *
 * @returns the dialog's state and its submit
 */
export function useManagedAssetFormDialog(
  options: UseManagedAssetFormDialogOptions,
): UseManagedAssetFormDialogReturn {
  const { editMode, form, modelValue, onSaved } = options;

  const { t } = useI18n({ useScope: 'global' });

  const loading = shallowRef<boolean>(false);
  const modelErrorMessages = ref<ValidationErrors>({});

  const { setMessage } = useMessageStore();
  const { deleteCacheKey } = useAssetInfoCache();

  const dialogTitle = computed<string>(() =>
    toValue(editMode) ? t('asset_management.edit_title') : t('asset_management.add_title'),
  );

  function reportWholePayloadFailure(errors: ValidationErrors): void {
    const underlyingTokens = 'underlyingTokens' in errors ? errors.underlyingTokens : undefined;
    if (underlyingTokens) {
      const messages = Array.isArray(underlyingTokens) ? underlyingTokens : [underlyingTokens];
      setMessage({
        description: messages.join(','),
        title: t('asset_form.underlying_tokens'),
      });
      return;
    }

    const schema = errors.Schema;
    if (Array.isArray(schema)) {
      setMessage({
        description: schema[0],
        title: t('asset_form.underlying_tokens'),
      });
    }
  }

  function handleSaveError(error: unknown): void {
    let errors: string | ValidationErrors = getErrorMessage(error);
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors({});

    if (typeof errors === 'string') {
      setMessage({
        description: errors,
        title: toValue(editMode) ? t('asset_form.edit_error') : t('asset_form.add_error'),
      });
      return;
    }

    if (MESSAGE_ONLY_KEYS.some(key => key in errors))
      reportWholePayloadFailure(errors);

    set(modelErrorMessages, omit(errors, [...MESSAGE_ONLY_KEYS]));
    toValue(form)?.validate();
  }

  async function save(): Promise<boolean> {
    if (!isDefined(modelValue))
      return false;

    const formRef = toValue(form);
    if (!formRef?.validate())
      return false;

    set(loading, true);
    try {
      const identifier = await formRef.saveAsset();
      if (!identifier)
        return false;

      deleteCacheKey(identifier);
      formRef.saveIcon(identifier);
      set(modelValue, undefined);
      onSaved();
      return true;
    }
    catch (error: unknown) {
      handleSaveError(error);
      return false;
    }
    finally {
      set(loading, false);
    }
  }

  return {
    dialogTitle,
    loading: readonly(loading),
    modelErrorMessages,
    save,
  };
}
