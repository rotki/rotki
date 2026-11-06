import type { SupportedAsset } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { omit } from 'es-toolkit';
import { isErr, type Result } from 'plainfp/result';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

/**
 * The error keys the dialog names above the form rather than on a field.
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
  saveIcon: (identifier: string) => Promise<Result<void, unknown>>;
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
  /** Why the last write failed where no field is to blame, named in the dialog; Save is the retry. */
  failure: Readonly<Ref<NamedFailure | undefined>>;
  /** Field errors returned by the server. */
  modelErrorMessages: Ref<ValidationErrors>;
  /** Whether a write is in flight. */
  loading: Readonly<Ref<boolean>>;
  /**
   * Validates and writes the asset, then uploads its icon.
   *
   * @remarks
   * When the asset lands but its icon does not, the list is refreshed and the dialog stays open
   * naming the upload's failure; the next save retries only the icon, since writing the asset again
   * would add it a second time.
   *
   * @returns whether both landed; `false` leaves the dialog open with the reason shown
   */
  save: () => Promise<boolean>;
}

/**
 * Drives the managed asset dialog: validating, writing through the form, and splitting a failure
 * between the fields it belongs to and a failure named above the form for the rest.
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

  const { clear: clearFailure, failure, report } = useFailureSlot();
  const { deleteCacheKey } = useAssetInfoCache();

  /** The asset a save already wrote while its icon upload failed, so a retry skips the write. */
  const writtenIdentifier = shallowRef<string>();

  const dialogTitle = computed<string>(() =>
    toValue(editMode) ? t('asset_management.edit_title') : t('asset_management.add_title'),
  );

  function reportWholePayloadFailure(errors: ValidationErrors): void {
    const underlyingTokens = 'underlyingTokens' in errors ? errors.underlyingTokens : undefined;
    if (underlyingTokens) {
      const messages = Array.isArray(underlyingTokens) ? underlyingTokens : [underlyingTokens];
      report(t('asset_form.underlying_tokens'), messages.join(','));
      return;
    }

    const schema = errors.Schema;
    if (Array.isArray(schema))
      report(t('asset_form.underlying_tokens'), schema[0]);
  }

  function handleSaveError(error: unknown): void {
    const errors = error instanceof ApiValidationError ? error.getValidationErrors({}) : undefined;

    if (errors === undefined || typeof errors === 'string') {
      report(toValue(editMode) ? t('asset_form.edit_error') : t('asset_form.add_error'), errors ?? error);
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
    clearFailure();
    try {
      let identifier = get(writtenIdentifier);
      if (!identifier) {
        identifier = await formRef.saveAsset();
        if (!identifier)
          return false;

        deleteCacheKey(identifier);
        onSaved();
      }

      const uploaded = await formRef.saveIcon(identifier);
      if (isErr(uploaded)) {
        set(writtenIdentifier, identifier);
        report(t('asset_form.icon_upload.failed'), uploaded.error);
        return false;
      }

      set(modelValue, undefined);
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

  watch(modelValue, (value) => {
    if (!value)
      set(writtenIdentifier, undefined);
  });

  return {
    dialogTitle,
    failure,
    loading: readonly(loading),
    modelErrorMessages,
    save,
  };
}
