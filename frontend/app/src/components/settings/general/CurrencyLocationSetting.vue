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
    <VRadioGroup
      v-model="currencyLocation"
      class="general-settings__fields__currency-location"
      :label="t('general_settings.amount.label.currency_location')"
      row
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    >
      <VRadio
        :label="t('general_settings.amount.label.location_before')"
        value="before"
      />
      <VRadio
        :label="t('general_settings.amount.label.location_after')"
        value="after"
      />
    </VRadioGroup>
  </SettingsOption>
</template>
