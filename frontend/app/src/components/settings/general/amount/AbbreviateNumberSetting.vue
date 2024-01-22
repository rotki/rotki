<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import { MINIMUM_DIGIT_TO_BE_ABBREVIATED } from '@/data/constraints';
import type { Ref } from 'vue';

const { t } = useI18n();

const abbreviate: Ref<boolean> = ref(false);
const minimumDigit: Ref<string> = ref(MINIMUM_DIGIT_TO_BE_ABBREVIATED.toString());
const { abbreviateNumber, minimumDigitToBeAbbreviated } = storeToRefs(useFrontendSettingsStore());

function resetMinimumDigitToBeAbbreviated() {
  set(minimumDigit, get(minimumDigitToBeAbbreviated).toString());
}

onMounted(() => {
  set(abbreviate, get(abbreviateNumber));
  resetMinimumDigitToBeAbbreviated();
});

const rules = {
  minimumDigit: {
    required: helpers.withMessage(
      t('general_settings.validation.minimum_digit_to_be_abbreviated.non_empty'),
      required,
    ),
    min: helpers.withMessage(
      t('general_settings.validation.minimum_digit_to_be_abbreviated.min_value', { min: MINIMUM_DIGIT_TO_BE_ABBREVIATED }),
      minValue(MINIMUM_DIGIT_TO_BE_ABBREVIATED),
    ),
  },
};

const v$ = useVuelidate(rules, { minimumDigit }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const transform = (value?: string) => (value ? Number.parseInt(value) : value);
</script>

<template>
  <div class="flex flex-col md:flex-row gap-8 mt-4">
    <SettingsOption
      #default="{ error, success, update }"
      setting="abbreviateNumber"
      frontend-setting
    >
      <VSwitch
        v-model="abbreviate"
        class="mt-0"
        data-cy="frontend-settings__fields__abbreviate_number"
        :label="t('frontend_settings.label.abbreviate_number')"
        :hint="t('frontend_settings.subtitle.abbreviate_number')"
        color="primary"
        persistent-hint
        :success-messages="success"
        :error-messages="error"
        @change="update($event)"
      />
    </SettingsOption>
    <SettingsOption
      #default="{ error, success, update }"
      :transform="transform"
      class="md:min-w-[18rem]"
      setting="minimumDigitToBeAbbreviated"
      frontend-setting
      @finished="resetMinimumDigitToBeAbbreviated()"
    >
      <RuiTextField
        v-model="minimumDigit"
        :disabled="!abbreviate"
        variant="outlined"
        color="primary"
        :min="MINIMUM_DIGIT_TO_BE_ABBREVIATED"
        data-cy="frontend-settings__fields__minimum_digit_to_be_abbreviated"
        :label="t('frontend_settings.label.minimum_digit_to_be_abbreviated')"
        :hint="t('frontend_settings.subtitle.minimum_digit_to_be_abbreviated')"
        type="number"
        :success-messages="success"
        :error-messages="
          error || toMessages(v$.minimumDigit)
        "
        @input="callIfValid($event, update)"
      />
    </SettingsOption>
  </div>
</template>
