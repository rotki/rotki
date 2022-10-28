<template>
  <div class="mt-8">
    <div class="text-h6">
      {{ tc('frontend_settings.subtitle.query') }}
    </div>
    <settings-option
      #default="{ error, success, update }"
      class="mt-1"
      setting="queryPeriod"
      frontend-setting
      :transform="transform"
      :error-message="tc('frontend_settings.validation.periodic_query.error')"
      @updated="restart"
      @finished="resetQueryPeriod"
    >
      <v-text-field
        v-model="queryPeriod"
        outlined
        class="general-settings__fields__periodic-client-query-period"
        :label="tc('frontend_settings.label.query_period')"
        :hint="tc('frontend_settings.label.query_period_hint')"
        type="number"
        :min="minQueryPeriod"
        :max="maxQueryPeriod"
        :success-messages="success"
        :error-messages="error || v$.queryPeriod.$errors.map(e => e.$message)"
        @change="callIfValid($event, update)"
      />
    </settings-option>
  </div>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { useValidation } from '@/composables/validation';
import { useMonitorStore } from '@/store/monitor';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const queryPeriod = ref<string>('5');
const minQueryPeriod = 5;
const maxQueryPeriod = 3600;

const { t, tc } = useI18n();

const rules = {
  queryPeriod: {
    required: helpers.withMessage(
      t('frontend_settings.validation.periodic_query.non_empty').toString(),
      required
    ),
    between: helpers.withMessage(
      t('frontend_settings.validation.periodic_query.invalid_period', {
        start: minQueryPeriod,
        end: maxQueryPeriod
      }).toString(),
      between(minQueryPeriod, maxQueryPeriod)
    )
  }
};

const { queryPeriod: currentPeriod } = storeToRefs(useFrontendSettingsStore());

const resetQueryPeriod = () => {
  set(queryPeriod, get(currentPeriod).toString());
};

const v$ = useVuelidate(rules, { queryPeriod }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { restart } = useMonitorStore();

const transform = (value: string) => (value ? parseInt(value) : value);

onMounted(() => {
  resetQueryPeriod();
});
</script>
