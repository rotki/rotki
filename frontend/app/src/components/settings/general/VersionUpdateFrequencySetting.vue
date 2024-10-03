<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, requiredIf } from '@vuelidate/validators';
import { Constraints } from '@/data/constraints';
import { toMessages } from '@/utils/validation';

const versionUpdateCheckFrequency = ref<string>('');
const versionUpdateCheckEnabled = ref<boolean>(false);
const { versionUpdateCheckFrequency: existingFrequency } = storeToRefs(useFrontendSettingsStore());
const maxVersionUpdateCheckFrequency = Constraints.MAX_HOURS_DELAY;
const { t } = useI18n();

const rules = {
  versionUpdateCheckFrequency: {
    required: helpers.withMessage(
      t('general_settings.version_update_check.validation.non_empty'),
      requiredIf(versionUpdateCheckEnabled),
    ),
    between: helpers.withMessage(
      t('general_settings.version_update_check.validation.invalid_frequency', {
        start: 1,
        end: maxVersionUpdateCheckFrequency,
      }),
      between(1, Constraints.MAX_HOURS_DELAY),
    ),
  },
};

const v$ = useVuelidate(rules, { versionUpdateCheckFrequency }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetVersionUpdateCheckFrequency() {
  const frequency = get(existingFrequency);
  set(versionUpdateCheckEnabled, frequency > 0);
  set(versionUpdateCheckFrequency, get(versionUpdateCheckEnabled) ? frequency.toString() : '');
}

function frequencyTransform(value: string) {
  return value ? Number.parseInt(value) : value;
}

const switchTransform = (value: boolean) => (value ? 24 : -1);

onMounted(() => {
  resetVersionUpdateCheckFrequency();
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('general_settings.version_update_check.title') }}
    </template>
    <SettingsOption
      #default="{ updateImmediate }"
      setting="versionUpdateCheckFrequency"
      frontend-setting
      :transform="switchTransform"
      @finished="resetVersionUpdateCheckFrequency()"
    >
      <RuiSwitch
        v-model="versionUpdateCheckEnabled"
        class="mt-4"
        :label="t('general_settings.version_update_check.switch')"
        color="primary"
        @update:model-value="callIfValid($event, updateImmediate)"
      />
    </SettingsOption>
    <SettingsOption
      #default="{ error, success, update }"
      setting="versionUpdateCheckFrequency"
      frontend-setting
      :transform="frequencyTransform"
      :error-message="t('general_settings.version_update_check.validation.error')"
      @finished="resetVersionUpdateCheckFrequency()"
    >
      <div class="mt-4">
        <div class="text-rui-text text-body-2 mb-2">
          {{ t('general_settings.version_update_check.label') }}
        </div>
        <RuiTextField
          v-model="versionUpdateCheckFrequency"
          variant="outlined"
          color="primary"
          :disabled="!versionUpdateCheckEnabled"
          type="number"
          min="1"
          :max="maxVersionUpdateCheckFrequency"
          :placeholder="t('general_settings.version_update_check.label')"
          :hint="t('general_settings.version_update_check.hint')"
          :success-messages="success"
          :error-messages="error || toMessages(v$.versionUpdateCheckFrequency)"
          @update:model-value="update($event)"
        />
      </div>
    </SettingsOption>
  </SettingsItem>
</template>
