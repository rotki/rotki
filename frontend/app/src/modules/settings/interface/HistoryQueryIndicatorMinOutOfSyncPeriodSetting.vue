<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/modules/core/common/constraints';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const evmQueryIndicatorMinOutOfSyncPeriod = ref<string>('');

const minPeriod = 1;
const maxPeriod = Constraints.MAX_HOURS_DELAY;

const { t } = useI18n({ useScope: 'global' });

const rules = {
  evmQueryIndicatorMinOutOfSyncPeriod: {
    between: helpers.withMessage(
      t('frontend_settings.history_query_indicator.min_out_of_sync_period.validation.invalid_period', {
        end: maxPeriod,
        start: minPeriod,
      }),
      between(minPeriod, maxPeriod),
    ),
    required: helpers.withMessage(t('frontend_settings.history_query_indicator.min_out_of_sync_period.validation.non_empty'), required),
  },
};

const v$ = useVuelidate(rules, { evmQueryIndicatorMinOutOfSyncPeriod }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { evmQueryIndicatorMinOutOfSyncPeriod: currentPeriod } = storeToRefs(useFrontendSettingsStore());

function resetValue() {
  set(evmQueryIndicatorMinOutOfSyncPeriod, get(currentPeriod).toString());
}

const transform = (value: string) => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetValue();
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('frontend_settings.history_query_indicator.min_out_of_sync_period.title') }}
    </template>
    <template #subtitle>
      {{ t('frontend_settings.history_query_indicator.min_out_of_sync_period.subtitle') }}
    </template>
    <SettingsOption
      #default="{ error, success, update }"
      setting="evmQueryIndicatorMinOutOfSyncPeriod"
      frontend-setting
      :transform="transform"
      :error-message="t('frontend_settings.history_query_indicator.min_out_of_sync_period.validation.error')"
      @finished="resetValue()"
    >
      <RuiTextField
        v-model="evmQueryIndicatorMinOutOfSyncPeriod"
        variant="outlined"
        color="primary"
        type="number"
        :min="minPeriod"
        :max="maxPeriod"
        :label="t('frontend_settings.history_query_indicator.min_out_of_sync_period.label')"
        :success-messages="success"
        :error-messages="error || toMessages(v$.evmQueryIndicatorMinOutOfSyncPeriod)"
        @update:model-value="callIfValid($event, update)"
      />
    </SettingsOption>
  </SettingsItem>
</template>
