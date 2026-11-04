import type { MaybeRefOrGetter, Ref } from 'vue';
import type { ZodType } from 'zod';
import type { SettingFieldState } from '@/modules/settings/controls/setting-field-schemas';
import { type FormApi, useForm } from '@/modules/core/form/use-form';

interface UseSettingFieldOptions<T> {
  /** The setting's draft from `useSettingModel`; a valid submit writes into it. */
  model: Ref<T>;
  /** Validates the field under `SETTING_FIELD`. */
  schema: MaybeRefOrGetter<ZodType>;
  /** How the stored value shows in the text field. */
  toField: (value: T) => string;
  /** How the text field becomes the stored value. */
  fromField: (field: string) => T;
  /** Runs on every keystroke before validation, typically to clear the last save message. */
  onEdit?: () => void;
}

interface UseSettingFieldReturn {
  form: FormApi<SettingFieldState, SettingFieldState>;
  /** Takes a keystroke: updates the field and, when it parses, writes the setting. */
  onInput: (value: string) => Promise<void>;
}

/**
 * The text field of a setting control, validated before it reaches the setting.
 *
 * @remarks
 * Submitting is the persist: the form core only runs it when the field parses, so an invalid draft
 * never reaches `model`. A change to `model` from elsewhere (a reset, another tab) is mirrored back
 * into the field.
 */
export function useSettingField<T>(options: UseSettingFieldOptions<T>): UseSettingFieldReturn {
  const { fromField, model, onEdit, schema, toField } = options;

  const form = useForm<SettingFieldState, SettingFieldState>({
    initial: (): SettingFieldState => ({ value: toField(get(model)) }),
    schema,
    submit: async (payload: SettingFieldState): Promise<{ success: boolean }> => {
      set(model, fromField(payload.value));
      return Promise.resolve({ success: true });
    },
    transform: (state): SettingFieldState => ({ value: state.value }),
  });

  watch(model, (value) => {
    form.state.value = toField(value);
  });

  async function onInput(value: string): Promise<void> {
    onEdit?.();
    form.state.value = value;
    await form.submit();
  }

  return { form, onInput };
}
