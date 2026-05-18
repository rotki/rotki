<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/modules/core/common/constraints';
import { useValidation } from '@/modules/core/common/use-validation';
import { toMessages } from '@/modules/core/common/validation/validation';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const { autoDetectTokensCooldownHours } = storeToRefs(useFrontendSettingsStore());
const cooldownHours = ref<string>(get(autoDetectTokensCooldownHours).toString());
const { autoDetectTokens } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n({ useScope: 'global' });

const maxHours = Constraints.MAX_HOURS_DELAY;
const rules = {
  cooldownHours: {
    between: helpers.withMessage(
      t('general_settings.auto_detect_tokens_cooldown.validation.invalid_value', {
        end: maxHours,
        start: 1,
      }),
      between(1, maxHours),
    ),
    required: helpers.withMessage(
      t('general_settings.auto_detect_tokens_cooldown.validation.non_empty'),
      required,
    ),
  },
};
const v$ = useVuelidate(rules, { cooldownHours }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetCooldown(): void {
  set(cooldownHours, get(autoDetectTokensCooldownHours).toString());
}

function transform(value?: string): number | undefined {
  return value ? Number.parseInt(value, 10) : undefined;
}

watch(autoDetectTokensCooldownHours, () => {
  resetCooldown();
});
</script>

<template>
  <SettingsOption
    v-if="autoDetectTokens"
    frontend-setting
    setting="autoDetectTokensCooldownHours"
    :transform="transform"
    :error-message="t('general_settings.auto_detect_tokens_cooldown.validation.error')"
    :success-message="t('general_settings.auto_detect_tokens_cooldown.validation.success')"
    @finished="resetCooldown()"
  >
    <template #title>
      {{ t('general_settings.auto_detect_tokens_cooldown.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.auto_detect_tokens_cooldown.subtitle') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiTextField
        v-model="cooldownHours"
        variant="outlined"
        color="primary"
        min="1"
        :max="maxHours"
        data-cy="auto-detect-tokens-cooldown-input"
        class="w-full"
        :label="t('general_settings.auto_detect_tokens_cooldown.label')"
        type="number"
        :success-messages="success"
        :error-messages="error || toMessages(v$.cooldownHours)"
        @update:model-value="callIfValid($event, update)"
      />
    </template>
  </SettingsOption>
</template>
