<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue } from '@vuelidate/validators';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
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

const multiplier = ref<string>(String(get(model)));

const rules = {
  multiplier: {
    min: helpers.withMessage(t('statistics_graph_settings.multiplier.validations.positive_number'), minValue(0)),
  },
};
const v$ = useVuelidate(rules, { multiplier }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const numericMultiplier = computed<number>(() => {
  const multi = Number.parseInt(get(multiplier));
  return isNaN(multi) ? 0 : multi;
});

const period = computed<number>(() => {
  const multi = get(numericMultiplier);
  if (multi <= 0)
    return 0;

  return multi * get(balanceSaveFrequency);
});

function persist(): void {
  set(model, get(numericMultiplier));
}

function onInput(value: string): void {
  clearAll();
  callIfValid(value, persist);
}

watch(model, (value) => {
  if (String(value) !== get(multiplier))
    set(multiplier, String(value));
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
      v-model="multiplier"
      variant="outlined"
      color="primary"
      min="0"
      :label="t('statistics_graph_settings.multiplier.label')"
      type="number"
      :success-messages="success"
      :error-messages="error || toMessages(v$.multiplier)"
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
