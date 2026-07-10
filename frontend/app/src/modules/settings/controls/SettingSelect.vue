<script setup lang="ts" generic="TOption = string">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for a single-choice setting. Given a registry key it manages its own draft
 * and persistence through `useSettingModel`, and surfaces the same "Settings saved" / error messages
 * the hand-written selects did. Renders a `RuiMenuSelect` (default) or a `RuiRadioGroup` depending on
 * `control`. Put it inside a `SettingsItem` for the title/subtitle; this renders only the control.
 *
 * `options` may be primitives or objects; for objects pass `keyAttr`/`textAttr` to project the stored
 * value and the displayed text. Options are normalised to `{ value, label }` internally, so bespoke
 * item rendering goes through the `#item` slot (select) or `#option` slot (radio), which both receive
 * the original option.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  options,
  keyAttr,
  textAttr,
  label = '',
  control = 'select',
  successMessage = '',
  errorMessage = '',
  debounce = 0,
  // eslint-disable-next-line vue/max-props -- a generic owning control needs the full setting/options/label/message surface
} = defineProps<{
  setting: WritableSettingKeyOf<string>;
  options: readonly TOption[];
  /** For object options, the property projected as the stored value. Omit for primitive options. */
  keyAttr?: string;
  /** For object options, the property shown as the label. Omit for primitive options. */
  textAttr?: string;
  label?: string;
  control?: 'select' | 'radio';
  /** Static text, or a callback given the persisted value. */
  successMessage?: string | ((value: string) => string);
  /** Static prefix, or a callback given the persisted value. Prefixed before the writer error. */
  errorMessage?: string | ((value: string) => string);
  debounce?: number;
}>();

const emit = defineEmits<{
  /** Fired after a successful persist, mirroring the old `SettingsOption` `@finished` hook. */
  updated: [value: string];
}>();

const { error: writeError, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

// Bind the control to a concrete string ref: the writer key is constrained to string-valued settings
// (enums are string enums), so the draft round-trips as a string and this keeps the child's generic
// inference simple.
const selected = computed<string>({
  get: () => get(model),
  set: (value) => {
    set(model, value);
  },
});

function optionValue(option: TOption): string {
  return keyAttr ? String(Reflect.get(new Object(option), keyAttr)) : String(option);
}

function optionLabel(option: TOption): string {
  return textAttr ? String(Reflect.get(new Object(option), textAttr)) : String(option);
}

interface NormalisedOption {
  value: string;
  label: string;
  raw: TOption;
}

const normalised = computed<NormalisedOption[]>(() =>
  options.map(option => ({ label: optionLabel(option), raw: option, value: optionValue(option) })),
);

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved) {
    setSuccess(typeof successMessage === 'function' ? successMessage(get(model)) : successMessage, true);
    emit('updated', get(model));
  }
});

watch(writeError, (message) => {
  if (message) {
    const prefix = typeof errorMessage === 'function' ? errorMessage(get(model)) : errorMessage;
    setError(prefix ? `${prefix}: ${message}` : message, true);
  }
});
</script>

<template>
  <RuiRadioGroup
    v-if="control === 'radio'"
    v-bind="$attrs"
    v-model="selected"
    color="primary"
    :success-messages="success"
    :error-messages="error"
  >
    <RuiRadio
      v-for="option in normalised"
      :key="option.value"
      :value="option.value"
    >
      <slot
        name="option"
        :option="option.raw"
      >
        {{ option.label }}
      </slot>
    </RuiRadio>
  </RuiRadioGroup>
  <RuiMenuSelect
    v-else
    v-bind="$attrs"
    v-model="selected"
    variant="outlined"
    color="primary"
    :options="normalised"
    :label="label"
    key-attr="value"
    text-attr="label"
    :success-messages="success"
    :error-messages="error"
  >
    <template #item="{ item }">
      <slot
        name="item"
        :item="item.raw"
      >
        {{ item.label }}
      </slot>
    </template>
    <template
      v-if="$slots.selection"
      #selection="{ item }"
    >
      <slot
        name="selection"
        :item="item.raw"
      />
    </template>
  </RuiMenuSelect>
</template>
