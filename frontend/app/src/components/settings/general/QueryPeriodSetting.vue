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
      @updated="restartMonitor"
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
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { useValidation } from '@/composables/validation';
import i18n from '@/i18n';
import { monitor } from '@/services/monitoring';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const queryPeriod = ref<string>('5');
const minQueryPeriod = 5;
const maxQueryPeriod = 3600;

const rules = {
  queryPeriod: {
    required: helpers.withMessage(
      i18n
        .t('frontend_settings.validation.periodic_query.non_empty')
        .toString(),
      required
    ),
    between: helpers.withMessage(
      i18n
        .t('frontend_settings.validation.periodic_query.invalid_period', {
          start: minQueryPeriod,
          end: maxQueryPeriod
        })
        .toString(),
      between(minQueryPeriod, maxQueryPeriod)
    )
  }
};

const { queryPeriod: currentPeriod } = storeToRefs(useFrontendSettingsStore());
const { tc } = useI18n();

const resetQueryPeriod = () => {
  set(queryPeriod, get(currentPeriod).toString());
};

const v$ = useVuelidate(rules, { queryPeriod }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const restartMonitor = () => {
  monitor.restart();
};

const transform = (value: string) => (value ? parseInt(value) : value);

onMounted(() => {
  resetQueryPeriod();
});
</script>
