<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { useGeneralSettingsStore } from '@/store/settings/general';

const queryRetryLimit = ref<string>('5');
const minPeriod = 1;

const { t } = useI18n();

const rules = {
  queryRetryLimit: {
    required: helpers.withMessage(
      t(
        'general_settings.external_service_setting.validation.query_retry_limit.non_empty'
      ).toString(),
      required
    ),
    min: helpers.withMessage(
      t(
        'general_settings.external_service_setting.validation.query_retry_limit.invalid_range',
        {
          min: minPeriod
        }
      ).toString(),
      minValue(minPeriod)
    )
  }
};

const { queryRetryLimit: currentPeriod } = storeToRefs(
  useGeneralSettingsStore()
);

const resetQueryPeriod = () => {
  set(queryRetryLimit, get(currentPeriod).toString());
};

const v$ = useVuelidate(rules, { queryRetryLimit }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { restart } = useMonitorStore();

const transform = (value: string) => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetQueryPeriod();
});
</script>

<template>
  <div>
    <SettingsOption
      #default="{ error, success, update }"
      class="mt-1"
      setting="queryRetryLimit"
      :transform="transform"
      @updated="restart()"
      @finished="resetQueryPeriod()"
    >
      <VTextField
        v-model="queryRetryLimit"
        outlined
        class="general-settings__fields__query_retry_limit"
        :label="
          t('general_settings.external_service_setting.label.query_retry_limit')
        "
        :hint="
          t(
            'general_settings.external_service_setting.label.query_retry_limit_hint'
          )
        "
        persistent-hint
        type="number"
        :min="minPeriod"
        :success-messages="success"
        :error-messages="
          error || v$.queryRetryLimit.$errors.map(e => e.$message)
        "
        @change="callIfValid($event, update)"
      />
    </SettingsOption>
  </div>
</template>
