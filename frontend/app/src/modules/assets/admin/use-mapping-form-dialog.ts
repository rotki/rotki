import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

interface MappingFormHandle {
  /** Runs the form's own validation. */
  validate: () => boolean;
}

interface UseMappingFormDialogOptions<T, TPayload> {
  /** Writes a new mapping. */
  add: (payload: TPayload) => Promise<boolean>;
  /** Whether the dialog is editing rather than creating. */
  editMode: MaybeRefOrGetter<boolean>;
  /** Writes an existing mapping. */
  edit: (payload: TPayload) => Promise<boolean>;
  /** The form component, which owns validation. */
  form: MaybeRefOrGetter<MappingFormHandle | null | undefined>;
  /** The mapping being edited, cleared once the write lands. */
  modelValue: Ref<T | undefined>;
  /** Called with the mapping that was written, so the caller can refresh its list. */
  onSaved: (mapping: T) => void;
  /** Turns the edited mapping into what the endpoint takes. */
  toPayload: (mapping: T) => TPayload;
}

interface UseMappingFormDialogReturn {
  /** The dialog's title, which differs between adding and editing. */
  dialogTitle: ComputedRef<string>;
  /** Why the last write failed, named as an add or an edit failure in the dialog; Save is the retry. */
  failure: Readonly<Ref<NamedFailure | undefined>>;
  /** Whether a write is in flight. */
  loading: Readonly<Ref<boolean>>;
  /** Field errors, which the form binds. */
  modelErrorMessages: Ref<ValidationErrors>;
  /**
   * Validates and writes the mapping.
   *
   * @returns whether it landed; `false` leaves the dialog open with the reason shown
   */
  save: () => Promise<boolean>;
}

/**
 * The write flow the asset-mapping dialogs share: validate, add or edit, then close and hand the
 * mapping back on success.
 *
 * @returns the dialog's state and its submit
 */
export function useMappingFormDialog<T, TPayload = T>(
  options: UseMappingFormDialogOptions<T, TPayload>,
): UseMappingFormDialogReturn {
  const { add, edit, editMode, form, modelValue, onSaved, toPayload } = options;

  const { t } = useI18n({ useScope: 'global' });

  const loading = shallowRef<boolean>(false);
  const modelErrorMessages = ref<ValidationErrors>({});

  const { clear: clearFailure, failure, report } = useFailureSlot();

  const dialogTitle = computed<string>(() =>
    toValue(editMode)
      ? t('asset_management.cex_mapping.edit_title')
      : t('asset_management.cex_mapping.add_title'),
  );

  async function save(): Promise<boolean> {
    if (!isDefined(modelValue))
      return false;

    if (!toValue(form)?.validate())
      return false;

    const mapping = get(modelValue);
    const payload = toPayload(mapping);

    set(loading, true);
    clearFailure();
    let success: boolean;
    try {
      success = toValue(editMode) ? await edit(payload) : await add(payload);
    }
    catch (error: unknown) {
      success = false;
      report(
        toValue(editMode)
          ? t('asset_management.cex_mapping.edit_error')
          : t('asset_management.cex_mapping.add_error'),
        error,
      );
    }
    set(loading, false);

    if (success) {
      set(modelValue, undefined);
      onSaved(mapping);
    }
    return success;
  }

  return {
    dialogTitle,
    failure,
    loading: readonly(loading),
    modelErrorMessages,
    save,
  };
}
