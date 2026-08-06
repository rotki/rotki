<script setup lang="ts">
import type { ZodType } from 'zod';
import { useForm } from '@/modules/core/form/use-form';
import { numberSettingSchema, SETTING_FIELD, type SettingFieldState } from '@/modules/settings/controls/setting-field-schemas';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingModel } from '@/modules/settings/use-setting-model';

const emit = defineEmits<{
  updated: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const balanceSaveFrequency = useSetting('balanceSaveFrequency');
const { error: writeError, model, success: writeSuccess } = useSettingModel('ssfGraphMultiplier', { debounce: 1500 });
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

// A blank field is not an error: it persists as zero, which turns the graph off.
const schema = computed<ZodType>(() => numberSettingSchema({
  messages: {
    min: t('statistics_graph_settings.multiplier.validations.positive_number'),
    required: t('statistics_graph_settings.multiplier.validations.positive_number'),
  },
  min: 0,
  required: false,
}));

function toMultiplier(value: string): number {
  const multi = Number.parseInt(value);
  return isNaN(multi) ? 0 : multi;
}

/** Submitting is the persist: the core runs it only when the field parses, as `callIfValid` did. */
const form = useForm<SettingFieldState, SettingFieldState>({
  initial: (): SettingFieldState => ({ value: String(get(model)) }),
  schema,
  submit: async (payload: SettingFieldState): Promise<{ success: boolean }> => {
    set(model, toMultiplier(payload.value));
    return Promise.resolve({ success: true });
  },
  transform: (state): SettingFieldState => ({ value: state.value }),
});

const numericMultiplier = computed<number>(() => toMultiplier(form.state.value));

const period = computed<number>(() => {
  const multi = get(numericMultiplier);
  if (multi <= 0)
    return 0;

  return multi * get(balanceSaveFrequency);
});

async function onInput(value: string): Promise<void> {
  clearAll();
  form.state.value = value;
  await form.submit();
}

// Reflect external changes into the field, but ignore the echo of our own writes (same string).
watch(model, (value) => {
  if (String(value) !== form.state.value)
    form.state.value = String(value);
});

watch(writeSuccess, (saved) => {
  if (saved) {
    setSuccess('', true);
    emit('updated');
  }
});

watch(writeError, (message) => {
  if (message)
    setError(message, true);
});
</script>

<template>
  <div>
    <RuiCardHeader class="p-0 mb-6">
      <template #header>
        {{ t('statistics_graph_settings.multiplier.title') }}
      </template>
      <template #subheader>
        {{ t('statistics_graph_settings.multiplier.subtitle') }}
      </template>
    </RuiCardHeader>
    <RuiTextField
      v-model="form.state.value"
      variant="outlined"
      color="primary"
      min="0"
      :label="t('statistics_graph_settings.multiplier.label')"
      type="number"
      :success-messages="success"
      :error-messages="error || form.errors(SETTING_FIELD)"
      @update:model-value="onInput($event)"
    />

    <div class="text-body-2 text-rui-text-secondary mt-2">
      <span v-if="period === 0">
        {{ t('statistics_graph_settings.multiplier.off') }}
      </span>
      <span v-else>
        {{ t('statistics_graph_settings.multiplier.on', { period }) }}
      </span>
    </div>
  </div>
</template>
