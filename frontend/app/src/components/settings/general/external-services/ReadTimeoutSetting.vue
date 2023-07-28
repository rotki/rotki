<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { useGeneralSettingsStore } from '@/store/settings/general';

const readTimeout = ref<string>('5');
const minPeriod = 1;

const { t } = useI18n();

const rules = {
  readTimeout: {
    required: helpers.withMessage(
      t(
        'general_settings.external_service_setting.validation.read_timeout.non_empty'
      ).toString(),
      required
    ),
    min: helpers.withMessage(
      t(
        'general_settings.external_service_setting.validation.read_timeout.invalid_range',
        {
          min: minPeriod
        }
      ).toString(),
      minValue(minPeriod)
    )
  }
};

const { readTimeout: currentPeriod } = storeToRefs(useGeneralSettingsStore());

const resetQueryPeriod = () => {
  set(readTimeout, get(currentPeriod).toString());
};

const v$ = useVuelidate(rules, { readTimeout }, { $autoDirty: true });
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
      setting="readTimeout"
      :transform="transform"
      @updated="restart()"
      @finished="resetQueryPeriod()"
    >
      <VTextField
        v-model="readTimeout"
        outlined
        class="general-settings__fields__read_timeout"
        :label="
          t('general_settings.external_service_setting.label.read_timeout')
        "
        :hint="
          t('general_settings.external_service_setting.label.read_timeout_hint')
        "
        persistent-hint
        type="number"
        :min="minPeriod"
        :success-messages="success"
        :error-messages="error || v$.readTimeout.$errors.map(e => e.$message)"
        @change="callIfValid($event, update)"
      />
    </SettingsOption>
  </div>
</template>
