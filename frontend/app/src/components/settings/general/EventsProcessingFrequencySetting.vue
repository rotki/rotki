<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { Defaults } from '@/data/defaults';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';

const SECONDS_PER_HOUR = 3600;
const DEFAULT_FREQUENCY_HOURS = Defaults.DEFAULT_EVENTS_PROCESSING_FREQUENCY / SECONDS_PER_HOUR;
const MAX_FREQUENCY_HOURS = Math.floor(Constraints.MAX_SECONDS_DELAY / SECONDS_PER_HOUR);

const eventsProcessingFrequency = ref<string>(DEFAULT_FREQUENCY_HOURS.toString());

const { eventsProcessingFrequency: frequency } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n({ useScope: 'global' });

const rules = {
  eventsProcessingFrequency: {
    between: helpers.withMessage(
      t('general_settings.events_processing_frequency.validation.invalid_frequency', {
        end: MAX_FREQUENCY_HOURS,
        start: 1,
      }),
      between(1, MAX_FREQUENCY_HOURS),
    ),
    required: helpers.withMessage(t('general_settings.events_processing_frequency.validation.non_empty'), required),
  },
};
const v$ = useVuelidate(rules, { eventsProcessingFrequency }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetEventsProcessingFrequency(): void {
  const frequencyInHours = Math.floor(get(frequency) / SECONDS_PER_HOUR);
  set(eventsProcessingFrequency, frequencyInHours.toString());
}

function transform(value?: string): number | string | undefined {
  if (!value)
    return value;
  const hours = Number.parseInt(value);
  return hours * SECONDS_PER_HOUR;
}

function successMessage(frequencySeconds: string): string {
  const hours = Math.floor(Number.parseInt(frequencySeconds) / SECONDS_PER_HOUR);
  return t('general_settings.events_processing_frequency.validation.success', {
    frequency: hours,
  });
}

function reset(update: (value: number) => void): void {
  update(Defaults.DEFAULT_EVENTS_PROCESSING_FREQUENCY);
  set(eventsProcessingFrequency, DEFAULT_FREQUENCY_HOURS.toString());
}

onMounted(() => {
  resetEventsProcessingFrequency();
});
</script>

<template>
  <SettingsOption
    setting="eventsProcessingFrequency"
    :transform="transform"
    :error-message="t('general_settings.events_processing_frequency.validation.error')"
    :success-message="successMessage"
    @finished="resetEventsProcessingFrequency()"
  >
    <template #title>
      {{ t('general_settings.events_processing_frequency.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.events_processing_frequency.subtitle') }}
    </template>
    <template #default="{ error, success, update, updateImmediate }">
      <div class="flex items-start w-full">
        <RuiTextField
          v-model="eventsProcessingFrequency"
          variant="outlined"
          color="primary"
          min="1"
          :max="MAX_FREQUENCY_HOURS"
          data-cy="events-processing-frequency-input"
          class="w-full"
          :label="t('general_settings.events_processing_frequency.label')"
          type="number"
          :success-messages="success"
          :error-messages="error || toMessages(v$.eventsProcessingFrequency)"
          @update:model-value="callIfValid($event, update)"
        />

        <RuiButton
          class="mt-1 ml-2"
          variant="text"
          icon
          @click="reset(updateImmediate)"
        >
          <RuiIcon name="lu-history" />
        </RuiButton>
      </div>
    </template>
  </SettingsOption>
</template>
