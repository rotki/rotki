<script setup lang="ts">
import { CurrencyLocation } from '@/types/currency-location';

const currencyLocation = ref<CurrencyLocation>(CurrencyLocation.AFTER);
const { currencyLocation: location } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n();

const successMessage = (currencyLocation: CurrencyLocation) =>
  t('general_settings.validation.currency_location.success', {
    currencyLocation
  });

onMounted(() => {
  set(currencyLocation, get(location));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="currencyLocation"
    frontend-setting
    :error-message="t('general_settings.validation.currency_location.error')"
    :success-message="successMessage"
  >
    <RuiRadioGroup
      v-model="currencyLocation"
      color="primary"
      class="general-settings__fields__currency-location mt-4"
      :label="t('general_settings.amount.label.currency_location')"
      :success-messages="success"
      :error-messages="error"
      inline
      @input="update($event)"
    >
      <RuiRadio
        :label="t('general_settings.amount.label.location_before')"
        internal-value="before"
      />
      <RuiRadio
        :label="t('general_settings.amount.label.location_after')"
        internal-value="after"
      />
    </RuiRadioGroup>
  </SettingsOption>
</template>
