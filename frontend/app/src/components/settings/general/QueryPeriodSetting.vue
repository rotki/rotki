<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const queryPeriod = ref<string>('5');
const minQueryPeriod = 5;
const maxQueryPeriod = 3600;

const { t } = useI18n();

const rules = {
  queryPeriod: {
    required: helpers.withMessage(t('frontend_settings.periodic_query.validation.non_empty'), required),
    between: helpers.withMessage(
      t('frontend_settings.periodic_query.validation.invalid_period', {
        start: minQueryPeriod,
        end: maxQueryPeriod,
      }),
      between(minQueryPeriod, maxQueryPeriod),
    ),
  },
};

const { queryPeriod: currentPeriod } = storeToRefs(useFrontendSettingsStore());

function resetQueryPeriod() {
  set(queryPeriod, get(currentPeriod).toString());
}

const v$ = useVuelidate(rules, { queryPeriod }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { restart } = useMonitorStore();

const transform = (value: string) => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetQueryPeriod();
});
</script>

<template>
  <SettingsOption
    class="mt-1"
    setting="queryPeriod"
    frontend-setting
    :transform="transform"
    :error-message="t('frontend_settings.periodic_query.validation.error')"
    @updated="restart()"
    @finished="resetQueryPeriod()"
  >
    <template #title>
      {{ t('frontend_settings.periodic_query.title') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiTextField
        v-model="queryPeriod"
        variant="outlined"
        color="primary"
        class="general-settings__fields__periodic-client-query-period"
        :label="t('frontend_settings.periodic_query.label')"
        :hint="t('frontend_settings.periodic_query.hint')"
        type="number"
        :min="minQueryPeriod"
        :max="maxQueryPeriod"
        :success-messages="success"
        :error-messages="error || toMessages(v$.queryPeriod)"
        @update:model-value="callIfValid($event, update)"
      />
    </template>
  </SettingsOption>
</template>
