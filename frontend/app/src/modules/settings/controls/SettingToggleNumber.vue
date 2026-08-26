<script setup lang="ts">
import type { ZodType } from 'zod';
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useForm } from '@/modules/core/form/use-form';
import { numberSettingSchema, SETTING_FIELD, type SettingFieldState } from '@/modules/settings/controls/setting-field-schemas';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Owning component for a setting that pairs an enable switch with a numeric field on a **single** key.
 *
 * @remarks
 * Toggling on writes `enabledValue` and toggling off writes the `offValue` sentinel, which defaults
 * to -1; while enabled, the field edits the stored value. `toField` and `fromField` map between the
 * stored value and the field string, seconds against days say. Validation is `required` while
 * enabled, plus a range rule from `min` and `max`.
 *
 * Renders only the switch and the field, so wrap it in a `SettingsItem` for a header.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  switchLabel,
  fieldLabel,
  min,
  max,
  enabledValue,
  offValue = -1,
  toField = (stored: number): string => String(stored),
  fromField = (input: string): number => Number.parseInt(input),
  validation,
  success,
  errorMessage = '',
  switchTestId,
  fieldTestId,
  fieldHint,
  debounce = 1500,
  // eslint-disable-next-line vue/max-props -- a generic composite control needs the full switch+field/validation/message surface
} = defineProps<{
  setting: WritableSettingKeyOf<number | null | undefined>;
  switchLabel: string;
  fieldLabel: string;
  min: number;
  max?: number;
  /** Stored value written when the switch is toggled on. */
  enabledValue: number;
  /** Sentinel written when toggled off. */
  offValue?: number;
  /** Maps the stored number to the field string, seconds to days say. */
  toField?: (stored: number) => string;
  /** Maps the field string back to the stored number, days to seconds say. */
  fromField?: (input: string) => number;
  /** Validation messages: `invalid` for the range rule, `empty` for the required rule (while enabled). */
  validation: { invalid: string; empty: string };
  /** Optional per-action success copy for the toggle and the field. */
  success?: { onToggle?: (enabled: boolean) => string; onValue?: (input: string) => string };
  errorMessage?: string;
  switchTestId?: string;
  fieldTestId?: string;
  fieldHint?: string;
  debounce?: number;
}>();

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success: successMessage } = useClearableMessages();

function fieldFor(value: number | null | undefined): string {
  return value && value > 0 ? toField(value) : '';
}

const initial = get(model);
const enabled = ref<boolean>(!!initial && initial > 0);
const pendingSuccess = ref<string>('');

/**
 * The value is only required while the toggle is on, and the toggle is not part of the field state,
 * so the schema is a getter rather than a value.
 */
const schema = computed<ZodType>(() => numberSettingSchema({
  max,
  messages: {
    between: validation.invalid,
    max: validation.invalid,
    min: validation.invalid,
    required: validation.empty,
  },
  min,
  required: get(enabled),
}));

const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: fieldFor(initial) }),
  schema,
  submit: async (payload: SettingFieldState): Promise<{ success: boolean }> => {
    set(pendingSuccess, success?.onValue ? success.onValue(payload.value) : '');
    set(model, payload.value ? fromField(payload.value) : offValue);
    return Promise.resolve({ success: true });
  },
  transform: (state): SettingFieldState => ({ value: state.value }),
});

watch(model, (value) => {
  set(enabled, !!value && value > 0);
  form.state.value = fieldFor(value);
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(get(pendingSuccess), true);
});

watch(writeError, (message) => {
  if (message)
    setError(errorMessage ? `${errorMessage}: ${message}` : message, true);
});

async function toggle(value: boolean): Promise<void> {
  clearAll();
  set(pendingSuccess, success?.onToggle ? success.onToggle(value) : '');
  set(model, value ? enabledValue : offValue);
  await flush();
}

/** Submitting is the persist: the core runs it only when the field parses, as `callIfValid` did. */
async function updateField(value: string): Promise<void> {
  clearAll();
  form.state.value = value;
  await form.submit();
}
</script>

<template>
  <div>
    <RuiSwitch
      v-model="enabled"
      :data-testid="switchTestId"
      :label="switchLabel"
      color="primary"
      :success-messages="successMessage"
      :error-messages="error"
      @update:model-value="toggle($event)"
    />
    <RuiTextField
      v-model="form.state.value"
      variant="outlined"
      color="primary"
      :data-testid="fieldTestId"
      class="pt-4"
      type="number"
      :min="min"
      :max="max"
      :disabled="!enabled"
      :label="fieldLabel"
      :hint="fieldHint"
      :success-messages="successMessage"
      :error-messages="enabled ? (error || form.errors(SETTING_FIELD)) : []"
      @update:model-value="updateField($event)"
    />
  </div>
</template>
