<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { useGeneralSettingsStore } from '@/store/settings/general';

const connectTimeout = ref<string>('30');
const minPeriod = 1;

const { t } = useI18n();

const rules = {
  connectTimeout: {
    required: helpers.withMessage(
      t(
        'general_settings.external_service_setting.validation.connect_timeout.non_empty'
      ).toString(),
      required
    ),
    min: helpers.withMessage(
      t(
        'general_settings.external_service_setting.validation.connect_timeout.invalid_range',
        {
          min: minPeriod
        }
      ).toString(),
      minValue(minPeriod)
    )
  }
};

const { connectTimeout: currentPeriod } = storeToRefs(
  useGeneralSettingsStore()
);

const resetQueryPeriod = () => {
  set(connectTimeout, get(currentPeriod).toString());
};

const v$ = useVuelidate(rules, { connectTimeout }, { $autoDirty: true });
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
      setting="connectTimeout"
      :transform="transform"
      @updated="restart()"
      @finished="resetQueryPeriod()"
    >
      <VTextField
        v-model="connectTimeout"
        outlined
        class="general-settings__fields__connect_timeout"
        :label="
          t('general_settings.external_service_setting.label.connect_timeout')
        "
        :hint="
          t(
            'general_settings.external_service_setting.label.connect_timeout_hint'
          )
        "
        persistent-hint
        type="number"
        :min="minPeriod"
        :success-messages="success"
        :error-messages="
          error || v$.connectTimeout.$errors.map(e => e.$message)
        "
        @change="callIfValid($event, update)"
      />
    </SettingsOption>
  </div>
</template>
