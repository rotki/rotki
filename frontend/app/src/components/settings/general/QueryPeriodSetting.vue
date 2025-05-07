<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useMonitorStore } from '@/store/monitor';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';

const queryPeriod = ref<string>('5');
const minQueryPeriod = 5;
const maxQueryPeriod = 3600;

const { t } = useI18n({ useScope: 'global' });

const rules = {
  queryPeriod: {
    between: helpers.withMessage(
      t('frontend_settings.periodic_query.validation.invalid_period', {
        end: maxQueryPeriod,
        start: minQueryPeriod,
      }),
      between(minQueryPeriod, maxQueryPeriod),
    ),
    required: helpers.withMessage(t('frontend_settings.periodic_query.validation.non_empty'), required),
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
