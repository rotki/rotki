<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, minValue } from '@vuelidate/validators';

const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const updated = () => emit('updated');

const multiplier = ref<string>('0');

const { balanceSaveFrequency, ssfGraphMultiplier: multiplierSetting } = storeToRefs(useGeneralSettingsStore());

const rules = {
  multiplier: {
    min: helpers.withMessage(t('statistics_graph_settings.multiplier.validations.positive_number'), minValue(0)),
  },
};
const v$ = useVuelidate(rules, { multiplier }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const numericMultiplier = computed(() => {
  const multi = Number.parseInt(get(multiplier));
  return isNaN(multi) ? 0 : multi;
});

const period = computed(() => {
  const multi = get(numericMultiplier);
  if (multi <= 0)
    return 0;

  return multi * get(balanceSaveFrequency);
});

function resetState() {
  set(multiplier, get(multiplierSetting).toString());
}

const transform = () => get(numericMultiplier);

function finished() {
  resetState();
  updated();
}

onMounted(() => {
  resetState();
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
    <SettingsOption
      #default="{ error, success, update }"
      setting="ssfGraphMultiplier"
      :transform="transform"
      @finished="finished()"
    >
      <RuiTextField
        v-model="multiplier"
        variant="outlined"
        color="primary"
        min="0"
        :label="t('statistics_graph_settings.multiplier.label')"
        type="number"
        :messages="success"
        :error-messages="error || toMessages(v$.multiplier)"
        @update:model-value="callIfValid($event, update)"
      />
    </SettingsOption>

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
