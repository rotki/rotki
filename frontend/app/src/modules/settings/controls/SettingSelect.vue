<script setup lang="ts" generic="TOption = string">
import type { RuiMenuSelect, RuiRadioGroup } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useSettingOptions } from '@/modules/settings/controls/use-setting-options';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import { resolveSettingMessage, useSettingWriteFeedback } from '@/modules/settings/use-setting-write-feedback';

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
} & /* @vue-ignore */ ForwardedProps<typeof RuiRadioGroup, Record<'setting' | 'options' | 'keyAttr' | 'textAttr' | 'label' | 'control' | 'successMessage' | 'errorMessage' | 'debounce', unknown>> & /* @vue-ignore */ ForwardedProps<typeof RuiMenuSelect, Record<'setting' | 'options' | 'keyAttr' | 'textAttr' | 'label' | 'control' | 'successMessage' | 'errorMessage' | 'debounce', unknown>>>();

const emit = defineEmits<{
  /** Fired after a successful persist, mirroring the old `SettingsOption` `@finished` hook. */
  updated: [value: string];
}>();

defineSlots<{
  option: (props: { option: TOption }) => any;
  item: (props: { item: TOption }) => any;
  selection: (props: { item: TOption }) => any;
}>();

const { error: writeError, model, success: writeSuccess } = useSettingModel(setting, { debounce });
const { error, success } = useSettingWriteFeedback(
  { error: writeError, model, success: writeSuccess },
  () => resolveSettingMessage(successMessage, get(model)),
  { errorPrefix: () => resolveSettingMessage(errorMessage, get(model)), onSaved: () => emit('updated', get(model)) },
);

/**
 * The draft the control binds to, as a concrete string rather than the setting's own type.
 *
 * @remarks
 * The writer key is constrained to string-valued settings, enums included, since those are string
 * enums. Naming the type here keeps the child's generic inference simple.
 */
const selected = computed<string>({
  get: () => get(model),
  set: (value) => {
    set(model, value);
  },
});

const normalised = useSettingOptions<TOption>({ keyAttr: () => keyAttr, options: () => options, textAttr: () => textAttr });
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
