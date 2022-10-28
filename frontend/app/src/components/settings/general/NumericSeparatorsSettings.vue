<template>
  <div>
    <settings-option
      #default="{ error, success, update }"
      setting="thousandSeparator"
      frontend-setting
      :error-message="
        tc('general_settings.validation.thousand_separator.error')
      "
      :success-message="thousandsSuccessMessage"
    >
      <v-text-field
        v-model="thousandSeparator"
        outlined
        maxlength="1"
        class="general-settings__fields__thousand-separator"
        :label="tc('general_settings.amount.label.thousand_separator')"
        type="text"
        :success-messages="success"
        :error-messages="
          error || v$.thousandSeparator.$errors.map(e => e.$message)
        "
        @change="callIfThousandsValid($event, update)"
      />
    </settings-option>

    <settings-option
      #default="{ error, success, update }"
      setting="decimalSeparator"
      frontend-setting
      :error-message="tc('general_settings.validation.decimal_separator.error')"
      :success-message="decimalsSuccessMessage"
    >
      <v-text-field
        v-model="decimalSeparator"
        outlined
        maxlength="1"
        class="general-settings__fields__decimal-separator"
        :label="tc('general_settings.amount.label.decimal_separator')"
        type="text"
        :success-messages="success"
        :error-messages="
          error || v$.decimalSeparator.$errors.map(e => e.$message)
        "
        @change="callIfDecimalsValid($event, update)"
      />
    </settings-option>
  </div>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, not, numeric, required, sameAs } from '@vuelidate/validators';
import { useValidation } from '@/composables/validation';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const thousandSeparator = ref<string>('');
const decimalSeparator = ref<string>('');

const { thousandSeparator: thousands, decimalSeparator: decimals } =
  storeToRefs(useFrontendSettingsStore());

const { tc } = useI18n();

const rules = {
  thousandSeparator: {
    required: helpers.withMessage(
      tc('general_settings.thousand_separator.validation.empty'),
      required
    ),
    notANumber: helpers.withMessage(
      tc(
        'general_settings.thousand_separator.validation.cannot_be_numeric_character'
      ),
      not(numeric)
    ),
    notTheSame: helpers.withMessage(
      tc('general_settings.thousand_separator.validation.cannot_be_the_same'),
      not(sameAs(decimalSeparator))
    )
  },
  decimalSeparator: {
    required: helpers.withMessage(
      tc('general_settings.decimal_separator.validation.empty'),
      required
    ),
    notANumber: helpers.withMessage(
      tc(
        'general_settings.decimal_separator.validation.cannot_be_numeric_character'
      ),
      not(numeric)
    ),
    notTheSame: helpers.withMessage(
      tc('general_settings.decimal_separator.validation.cannot_be_the_same'),
      not(sameAs(thousandSeparator))
    )
  }
};

const v$ = useVuelidate(
  rules,
  { thousandSeparator, decimalSeparator },
  { $autoDirty: true }
);

const { callIfValid } = useValidation(v$);

const callIfThousandsValid = (
  value: string,
  method: (value: string) => void
) => {
  let validator = get(v$);
  callIfValid(value, method, () => validator.thousandSeparator.$error);
};

const callIfDecimalsValid = (
  value: string,
  method: (value: string) => void
) => {
  let validator = get(v$);
  callIfValid(value, method, () => validator.decimalSeparator.$error);
};

const thousandsSuccessMessage = (thousandSeparator: string) =>
  tc('general_settings.validation.thousand_separator.success', 0, {
    thousandSeparator
  });

const decimalsSuccessMessage = (decimalSeparator: string) =>
  tc('general_settings.validation.decimal_separator.success', 0, {
    decimalSeparator
  });

onMounted(() => {
  set(thousandSeparator, get(thousands));
  set(decimalSeparator, get(decimals));
});
</script>
