<script setup lang="ts">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import useVuelidate from '@vuelidate/core';
import { between, helpers, minValue, requiredIf } from '@vuelidate/validators';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a setting that pairs an enable switch with a numeric field on a SINGLE
 * key: toggling on writes `enabledValue`, toggling off writes `offValue` (a sentinel, default -1), and
 * the field edits the stored value while enabled. Optional `toField`/`fromField` map between the stored
 * value and the field string (e.g. seconds<->days). Validation is `required` (only while enabled) plus
 * `between`/`minValue` from `min`/`max`. Renders only the switch + field; wrap it in a `SettingsItem`
 * for a header. Optional `success.onToggle`/`success.onValue` provide per-action success copy.
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
  /** Map the stored number to the field string (e.g. seconds -> days). */
  toField?: (stored: number) => string;
  /** Map the field string to the stored number (e.g. days -> seconds). */
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
const field = ref<string>(fieldFor(initial));
const pendingSuccess = ref<string>('');

const rules = {
  field: {
    ...(max !== undefined
      ? { between: helpers.withMessage(validation.invalid, between(min, max)) }
      : { minValue: helpers.withMessage(validation.invalid, minValue(min)) }),
    required: helpers.withMessage(validation.empty, requiredIf(enabled)),
  },
};

const v$ = useVuelidate(rules, { field }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

watch(model, (value) => {
  set(enabled, !!value && value > 0);
  set(field, fieldFor(value));
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

function updateField(value: string): void {
  clearAll();
  callIfValid(value, (input: string) => {
    set(pendingSuccess, success?.onValue ? success.onValue(input) : '');
    set(model, input ? fromField(input) : offValue);
  });
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
      v-model="field"
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
      :error-messages="enabled ? (error || toMessages(v$.field)) : []"
      @update:model-value="updateField($event)"
    />
  </div>
</template>
