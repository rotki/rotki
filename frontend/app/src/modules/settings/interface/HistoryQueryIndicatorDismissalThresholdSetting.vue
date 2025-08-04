<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';

const evmQueryIndicatorDismissalThreshold = ref<string>('');

const minThreshold = 1;
const maxThreshold = Constraints.MAX_HOURS_DELAY;

const { t } = useI18n({ useScope: 'global' });

const rules = {
  evmQueryIndicatorDismissalThreshold: {
    between: helpers.withMessage(
      t('frontend_settings.history_query_indicator.dismissal_threshold.validation.invalid_period', {
        end: maxThreshold,
        start: minThreshold,
      }),
      between(minThreshold, maxThreshold),
    ),
    required: helpers.withMessage(t('frontend_settings.history_query_indicator.dismissal_threshold.validation.non_empty'), required),
  },
};

const v$ = useVuelidate(rules, { evmQueryIndicatorDismissalThreshold }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { evmQueryIndicatorDismissalThreshold: currentThreshold } = storeToRefs(useFrontendSettingsStore());

function resetValue() {
  set(evmQueryIndicatorDismissalThreshold, get(currentThreshold).toString());
}

const transform = (value: string) => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetValue();
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('frontend_settings.history_query_indicator.dismissal_threshold.title') }}
    </template>
    <template #subtitle>
      {{ t('frontend_settings.history_query_indicator.dismissal_threshold.subtitle') }}
    </template>
    <SettingsOption
      #default="{ error, success, update }"
      setting="evmQueryIndicatorDismissalThreshold"
      frontend-setting
      :transform="transform"
      :error-message="t('frontend_settings.history_query_indicator.dismissal_threshold.validation.error')"
      @finished="resetValue()"
    >
      <RuiTextField
        v-model="evmQueryIndicatorDismissalThreshold"
        variant="outlined"
        color="primary"
        type="number"
        :min="minThreshold"
        :max="maxThreshold"
        :label="t('frontend_settings.history_query_indicator.dismissal_threshold.label')"
        :success-messages="success"
        :error-messages="error || toMessages(v$.evmQueryIndicatorDismissalThreshold)"
        @update:model-value="callIfValid($event, update)"
      />
    </SettingsOption>
  </SettingsItem>
</template>
