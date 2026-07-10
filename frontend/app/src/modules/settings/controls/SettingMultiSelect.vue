<script setup lang="ts" generic="TOption = string">
import type { WritableSettingKeyOf } from '@/modules/settings/settings-writer';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';

/**
 * Generic owning component for an array (multi-select) setting. Manages its own draft and persistence
 * through `useSettingModel` and renders a `RuiAutoComplete` bound to the stored key list. Options are
 * normalised to `{ value, label }` internally, so bespoke rendering goes through the `#item`/`#selection`
 * slots (both receive the original option). Set `bulk-actions` to show select-all / clear-all buttons.
 * Put it inside a `SettingsItem` for the title/subtitle.
 */
defineOptions({ inheritAttrs: false });

const {
  setting,
  options,
  keyAttr,
  textAttr,
  label = '',
  successMessage = '',
  errorMessage = '',
  bulkActions,
  debounce = 0,
} = defineProps<{
  setting: WritableSettingKeyOf<string[]>;
  options: readonly TOption[];
  /** The option property projected as the stored value. Omit for primitive options. */
  keyAttr?: string;
  /** The option property shown as the label. Omit for primitive options. */
  textAttr?: string;
  label?: string;
  successMessage?: string;
  /** Static prefix, prefixed before the writer error. */
  errorMessage?: string;
  /** When provided, renders select-all / clear-all buttons above the field with these labels. */
  bulkActions?: { selectLabel: string; clearLabel: string };
  debounce?: number;
}>();

const { error: writeError, model, pending, success: writeSuccess } = useSettingModel(setting, { debounce });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

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

const selected = computed<string[]>({
  get: () => get(model) ?? [],
  set: (value) => {
    set(model, value);
  },
});

const allSelected = computed<boolean>(() => get(normalised).length > 0 && get(selected).length === get(normalised).length);
const noneSelected = computed<boolean>(() => get(selected).length === 0);

function selectAll(): void {
  set(selected, get(normalised).map(option => option.value));
}

function clearSelection(): void {
  set(selected, []);
}

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(successMessage, true);
});

watch(writeError, (message) => {
  if (message)
    setError(errorMessage ? `${errorMessage}: ${message}` : message, true);
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      v-if="bulkActions"
      class="flex gap-2"
    >
      <RuiButton
        variant="text"
        size="sm"
        color="primary"
        :disabled="pending || allSelected"
        @click="selectAll()"
      >
        {{ bulkActions.selectLabel }}
      </RuiButton>
      <RuiButton
        variant="text"
        size="sm"
        color="primary"
        :disabled="pending || noneSelected"
        @click="clearSelection()"
      >
        {{ bulkActions.clearLabel }}
      </RuiButton>
    </div>
    <RuiAutoComplete
      v-bind="$attrs"
      v-model="selected"
      :options="normalised"
      :label="label"
      key-attr="value"
      text-attr="label"
      :success-messages="success"
      :error-messages="error"
      variant="outlined"
      chips
      auto-select-first
    >
      <template #selection="{ item }">
        <slot
          name="selection"
          :item="item.raw"
        />
      </template>
      <template #item="{ item }">
        <slot
          name="item"
          :item="item.raw"
        />
      </template>
    </RuiAutoComplete>
  </div>
</template>
