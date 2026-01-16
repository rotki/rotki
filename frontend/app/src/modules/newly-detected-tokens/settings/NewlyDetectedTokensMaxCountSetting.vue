<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';

const maxCount = ref<string>('500');

const { t } = useI18n({ useScope: 'global' });

const minCount = Constraints.NEWLY_DETECTED_TOKENS_MIN_COUNT;
const maxCountLimit = Constraints.NEWLY_DETECTED_TOKENS_MAX_COUNT;

const rules = {
  maxCount: {
    between: helpers.withMessage(
      t('frontend_settings.newly_detected_tokens.max_count.validation.invalid_range', {
        max: maxCountLimit,
        min: minCount,
      }),
      between(minCount, maxCountLimit),
    ),
    required: helpers.withMessage(t('frontend_settings.newly_detected_tokens.max_count.validation.non_empty'), required),
  },
};

const { newlyDetectedTokensMaxCount: currentMaxCount } = storeToRefs(useFrontendSettingsStore());

function resetMaxCount(): void {
  set(maxCount, get(currentMaxCount).toString());
}

const v$ = useVuelidate(rules, { maxCount }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const transform = (value: string): number | string => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetMaxCount();
});
</script>

<template>
  <SettingsOption
    class="mt-1"
    setting="newlyDetectedTokensMaxCount"
    frontend-setting
    :transform="transform"
    :error-message="t('frontend_settings.newly_detected_tokens.max_count.validation.error')"
    @finished="resetMaxCount()"
  >
    <template #title>
      {{ t('frontend_settings.newly_detected_tokens.max_count.title') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiTextField
        v-model="maxCount"
        variant="outlined"
        color="primary"
        :label="t('frontend_settings.newly_detected_tokens.max_count.label')"
        :hint="t('frontend_settings.newly_detected_tokens.max_count.hint')"
        type="number"
        :min="minCount"
        :max="maxCountLimit"
        :success-messages="success"
        :error-messages="error || toMessages(v$.maxCount)"
        @update:model-value="callIfValid($event, update)"
      />
    </template>
  </SettingsOption>
</template>
