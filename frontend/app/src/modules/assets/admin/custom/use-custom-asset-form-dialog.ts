import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { CustomAsset } from '@/modules/assets/types';
import { omit } from 'es-toolkit';
import { isErr, type Result } from 'plainfp/result';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

interface CustomAssetFormHandle {
  /** Runs the form's own validation. */
  validate: () => boolean;
  /** Uploads the pending icon for the saved asset. */
  saveIcon: (identifier: string) => Promise<Result<void, unknown>>;
}

interface UseCustomAssetFormDialogOptions {
  /** The asset being edited, or null when adding. */
  editableItem: MaybeRefOrGetter<CustomAsset | null | undefined>;
  /** The form component, which owns validation and the icon upload. */
  form: MaybeRefOrGetter<CustomAssetFormHandle | null | undefined>;
  /** Whether the dialog is open; it closes itself once a write lands. */
  open: Ref<boolean>;
  /** Called after a successful write, so the caller can refresh its list. */
  onSaved: (identifier: string) => void;
}

interface UseCustomAssetFormDialogReturn {
  /** The dialog's title, which differs between adding and editing. */
  dialogTitle: ComputedRef<string>;
  /** Why the last save failed where no field is to blame, named in the dialog; Save is the retry. */
  failure: Readonly<Ref<NamedFailure | undefined>>;
  /** Whether a write is in flight. */
  loading: Readonly<Ref<boolean>>;
  /** Field errors, which the form binds. */
  modelErrorMessages: Ref<ValidationErrors>;
  /**
   * The asset the form edits.
   *
   * @remarks
   * It mirrors `editableItem` while the dialog is open and is a blank asset when adding, so the
   * form always has something to bind even before anything is typed.
   */
  modelValue: Ref<CustomAsset | undefined>;
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

function emptyCustomAsset(): CustomAsset {
  return {
    customAssetType: '',
    identifier: '',
    name: '',
    notes: '',
  };
}

/**
 * Drives the custom asset dialog: mirroring the asset being edited, validating, and writing it.
 *
 * @returns the dialog's state and its submit
 */
export function useCustomAssetFormDialog(
  options: UseCustomAssetFormDialogOptions,
): UseCustomAssetFormDialogReturn {
  const { editableItem, form, onSaved, open } = options;

  const { t } = useI18n({ useScope: 'global' });

  const modelValue = ref<CustomAsset>();
  const modelErrorMessages = ref<ValidationErrors>({});
  const loading = shallowRef<boolean>(false);

  const { clear: clearFailure, failure, report } = useFailureSlot();
  const { addCustomAsset, editCustomAsset } = useAssetManagementApi();

  /** The asset a save already wrote while its icon upload failed, so a retry skips the write. */
  const writtenIdentifier = shallowRef<string>();

  const dialogTitle = computed<string>(() =>
    toValue(editableItem)
      ? t('asset_management.edit_title')
      : t('asset_management.add_title'),
  );

  /** Errors on fields of the asset go to those fields; anything else is named above the form. */
  function reportFailure(error: unknown, data: CustomAsset): void {
    const errors = error instanceof ApiValidationError ? error.getValidationErrors(data) : undefined;
    if (errors === undefined || typeof errors === 'string')
      report(toValue(editableItem) ? t('asset_management.edit_error') : t('asset_management.add_error'), errors ?? error);
    else
      set(modelErrorMessages, errors);
  }

  /** Writes the asset and resolves its identifier, or nothing when the backend did not take it. */
  async function writeAsset(data: CustomAsset): Promise<string | undefined> {
    if (toValue(editableItem))
      return (await editCustomAsset(data)) ? data.identifier : undefined;

    return (await addCustomAsset(omit(data, ['identifier']))) || undefined;
  }

  async function save(): Promise<boolean> {
    if (!isDefined(modelValue))
      return false;

    const formRef = toValue(form);
    if (!formRef?.validate())
      return false;

    const data = get(modelValue);
    set(loading, true);
    clearFailure();
    set(modelErrorMessages, {});
    try {
      let identifier = get(writtenIdentifier);
      if (!identifier) {
        identifier = await writeAsset(data);
        if (!identifier)
          return false;

        onSaved(identifier);
      }

      const uploaded = await formRef.saveIcon(identifier);
      if (isErr(uploaded)) {
        set(writtenIdentifier, identifier);
        report(t('asset_form.icon_upload.failed'), uploaded.error);
        return false;
      }

      set(open, false);
      return true;
    }
    catch (error: unknown) {
      reportFailure(error, data);
      return false;
    }
    finally {
      set(loading, false);
    }
  }

  function mirrorEditableItem([isOpen, item]: [boolean, CustomAsset | null | undefined]): void {
    clearFailure();
    set(writtenIdentifier, undefined);
    if (!isOpen) {
      set(modelValue, undefined);
      return;
    }

    set(modelValue, item ?? emptyCustomAsset());
  }

  watchImmediate([open, (): CustomAsset | null | undefined => toValue(editableItem)], mirrorEditableItem);

  return {
    dialogTitle,
    failure,
    loading: readonly(loading),
    modelErrorMessages,
    modelValue,
    save,
  };
}
