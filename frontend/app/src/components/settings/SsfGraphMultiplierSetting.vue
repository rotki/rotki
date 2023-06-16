<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const { t } = useI18n();

const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const updated = () => emit('updated');

const multiplier = ref<string>('0');

const { ssfGraphMultiplier: multiplierSetting, balanceSaveFrequency } =
  storeToRefs(useGeneralSettingsStore());

const rules = {
  multiplier: {
    min: helpers.withMessage(
      t('statistics_graph_settings.multiplier.validations.positive_number'),
      minValue(0)
    )
  }
};
const v$ = useVuelidate(rules, { multiplier }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const numericMultiplier = computed(() => {
  const multi = Number.parseInt(get(multiplier));
  return isNaN(multi) ? 0 : multi;
});

const period = computed(() => {
  const multi = get(numericMultiplier);
  if (multi <= 0) {
    return 0;
  }
  return multi * get(balanceSaveFrequency);
});

const resetState = () => {
  set(multiplier, get(multiplierSetting).toString());
};

const transform = () => get(numericMultiplier);

const finished = () => {
  resetState();
  updated();
};

onMounted(() => {
  resetState();
});
</script>

<template>
  <div>
    <card-title class="font-weight-medium mb-2">
      {{ t('statistics_graph_settings.multiplier.title') }}
    </card-title>
    <v-card-subtitle class="pa-0 mb-4">
      {{ t('statistics_graph_settings.multiplier.subtitle') }}
    </v-card-subtitle>
    <settings-option
      #default="{ error, success, update }"
      setting="ssfGraphMultiplier"
      :transform="transform"
      @finished="finished()"
    >
      <v-text-field
        v-model="multiplier"
        outlined
        min="0"
        :label="t('statistics_graph_settings.multiplier.label')"
        type="number"
        :success-messages="success"
        :error-messages="error || toMessages(v$.multiplier)"
        @change="callIfValid($event, update)"
      />
    </settings-option>

    <v-card-subtitle class="pa-0 mt-2">
      <span v-if="period === 0">
        {{ t('statistics_graph_settings.multiplier.off') }}
      </span>
      <span v-else>
        {{ t('statistics_graph_settings.multiplier.on', { period }) }}
      </span>
    </v-card-subtitle>
  </div>
</template>
