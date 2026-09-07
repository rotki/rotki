import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { CustomAsset } from '@/modules/assets/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { omit } from 'es-toolkit';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';

interface CustomAssetFormHandle {
  /** Runs the form's own validation. */
  validate: () => boolean;
  /** Uploads the pending icon for the saved asset. */
  saveIcon: (identifier: string) => void;
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
   * Validates and writes the asset.
   *
   * @returns whether it landed; `false` leaves the dialog open with the reason shown
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

  const { setMessage } = useMessageStore();
  const { addCustomAsset, editCustomAsset } = useAssetManagementApi();

  const dialogTitle = computed<string>(() =>
    toValue(editableItem)
      ? t('asset_management.edit_title')
      : t('asset_management.add_title'),
  );

  function reportFailure(error: unknown, editMode: boolean): void {
    const obj = { message: getErrorMessage(error) };
    setMessage({
      description: editMode
        ? t('asset_management.edit_error', obj)
        : t('asset_management.add_error', obj),
    });
  }

  async function save(): Promise<boolean> {
    if (!isDefined(modelValue))
      return false;

    const formRef = toValue(form);
    if (!formRef?.validate())
      return false;

    const data = get(modelValue);
    const editMode = !!toValue(editableItem);
    let identifier = data.identifier;
    let success: boolean;

    set(loading, true);
    try {
      if (editMode) {
        success = await editCustomAsset(data);
      }
      else {
        identifier = await addCustomAsset(omit(data, ['identifier']));
        success = !!identifier;
      }

      if (identifier)
        formRef.saveIcon(identifier);
    }
    catch (error: unknown) {
      success = false;
      reportFailure(error, editMode);
    }
    set(loading, false);

    if (success) {
      set(modelValue, undefined);
      onSaved(identifier);
    }
    return success;
  }

  function mirrorEditableItem([isOpen, item]: [boolean, CustomAsset | null | undefined]): void {
    if (!isOpen) {
      set(modelValue, undefined);
      return;
    }

    set(modelValue, item ?? emptyCustomAsset());
  }

  watchImmediate([open, (): CustomAsset | null | undefined => toValue(editableItem)], mirrorEditableItem);

  return {
    dialogTitle,
    loading: readonly(loading),
    modelErrorMessages,
    modelValue,
    save,
  };
}
