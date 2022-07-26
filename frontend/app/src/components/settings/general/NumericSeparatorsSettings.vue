<template>
  <div>
    <settings-option
      #default="{ error, success, update }"
      setting="thousandSeparator"
      frontend-setting
      :error-message="
        $tc('general_settings.validation.thousand_separator.error')
      "
      :success-message="
        thousandSeparator =>
          $tc('general_settings.validation.thousand_separator.success', 0, {
            thousandSeparator
          })
      "
    >
      <v-text-field
        v-model="thousandSeparator"
        outlined
        maxlength="1"
        class="general-settings__fields__thousand-separator"
        :label="$t('general_settings.amount.label.thousand_separator')"
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
      :error-message="
        $tc('general_settings.validation.decimal_separator.error')
      "
      :success-message="
        decimalSeparator =>
          $tc('general_settings.validation.decimal_separator.success', 0, {
            decimalSeparator
          })
      "
    >
      <v-text-field
        v-model="decimalSeparator"
        outlined
        maxlength="1"
        class="general-settings__fields__decimal-separator"
        :label="$t('general_settings.amount.label.decimal_separator')"
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
import { onMounted, ref } from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { helpers, not, numeric, required, sameAs } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';
import { useValidation } from '@/composables/validation';
import i18n from '@/i18n';

const thousandSeparator = ref<string>('');
const decimalSeparator = ref<string>('');

const { frontendSettings } = useSettings();

const rules = {
  thousandSeparator: {
    required: helpers.withMessage(
      i18n.t('general_settings.thousand_separator.validation.empty').toString(),
      required
    ),
    notANumber: helpers.withMessage(
      i18n
        .t(
          'general_settings.thousand_separator.validation.cannot_be_numeric_character'
        )
        .toString(),
      not(numeric)
    ),
    notTheSame: helpers.withMessage(
      i18n
        .t('general_settings.thousand_separator.validation.cannot_be_the_same')
        .toString(),
      not(sameAs(decimalSeparator))
    )
  },
  decimalSeparator: {
    required: helpers.withMessage(
      i18n.t('general_settings.decimal_separator.validation.empty').toString(),
      required
    ),
    notANumber: helpers.withMessage(
      i18n
        .t(
          'general_settings.decimal_separator.validation.cannot_be_numeric_character'
        )
        .toString(),
      not(numeric)
    ),
    notTheSame: helpers.withMessage(
      i18n
        .t('general_settings.decimal_separator.validation.cannot_be_the_same')
        .toString(),
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

onMounted(() => {
  const settings = get(frontendSettings);
  set(thousandSeparator, settings.thousandSeparator);
  set(decimalSeparator, settings.decimalSeparator);
});
</script>
