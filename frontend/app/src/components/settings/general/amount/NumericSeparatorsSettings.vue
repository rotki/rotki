<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, not, numeric, required, sameAs } from '@vuelidate/validators';
import Fragment from '@/components/helper/Fragment';

const thousandSeparator = ref<string>('');
const decimalSeparator = ref<string>('');

const { thousandSeparator: thousands, decimalSeparator: decimals } =
  storeToRefs(useFrontendSettingsStore());

const { t } = useI18n();

const rules = {
  thousandSeparator: {
    required: helpers.withMessage(
      t('general_settings.thousand_separator.validation.empty'),
      required
    ),
    notANumber: helpers.withMessage(
      t(
        'general_settings.thousand_separator.validation.cannot_be_numeric_character'
      ),
      not(numeric)
    ),
    notTheSame: helpers.withMessage(
      t('general_settings.thousand_separator.validation.cannot_be_the_same'),
      not(sameAs(decimalSeparator))
    )
  },
  decimalSeparator: {
    required: helpers.withMessage(
      t('general_settings.decimal_separator.validation.empty'),
      required
    ),
    notANumber: helpers.withMessage(
      t(
        'general_settings.decimal_separator.validation.cannot_be_numeric_character'
      ),
      not(numeric)
    ),
    notTheSame: helpers.withMessage(
      t('general_settings.decimal_separator.validation.cannot_be_the_same'),
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
  const validator = get(v$);
  callIfValid(value, method, () => validator.thousandSeparator.$error);
};

const callIfDecimalsValid = (
  value: string,
  method: (value: string) => void
) => {
  const validator = get(v$);
  callIfValid(value, method, () => validator.decimalSeparator.$error);
};

const thousandsSuccessMessage = (thousandSeparator: string) =>
  t('general_settings.validation.thousand_separator.success', {
    thousandSeparator
  });

const decimalsSuccessMessage = (decimalSeparator: string) =>
  t('general_settings.validation.decimal_separator.success', {
    decimalSeparator
  });

onMounted(() => {
  set(thousandSeparator, get(thousands));
  set(decimalSeparator, get(decimals));
});
</script>

<template>
  <Fragment>
    <SettingsOption
      #default="{ error, success, update }"
      setting="thousandSeparator"
      frontend-setting
      :error-message="t('general_settings.validation.thousand_separator.error')"
      :success-message="thousandsSuccessMessage"
    >
      <VTextField
        v-model="thousandSeparator"
        outlined
        maxlength="1"
        class="general-settings__fields__thousand-separator"
        :label="t('general_settings.amount.label.thousand_separator')"
        type="text"
        :success-messages="success"
        :error-messages="
          error || v$.thousandSeparator.$errors.map(e => e.$message)
        "
        @change="callIfThousandsValid($event, update)"
      />
    </SettingsOption>

    <SettingsOption
      #default="{ error, success, update }"
      setting="decimalSeparator"
      frontend-setting
      :error-message="t('general_settings.validation.decimal_separator.error')"
      :success-message="decimalsSuccessMessage"
    >
      <VTextField
        v-model="decimalSeparator"
        outlined
        maxlength="1"
        class="general-settings__fields__decimal-separator"
        :label="t('general_settings.amount.label.decimal_separator')"
        type="text"
        :success-messages="success"
        :error-messages="
          error || v$.decimalSeparator.$errors.map(e => e.$message)
        "
        @change="callIfDecimalsValid($event, update)"
      />
    </SettingsOption>
  </Fragment>
</template>
