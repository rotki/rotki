<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { CurrencyLocation } from '@/types/currency-location';

const currencyLocation = ref<CurrencyLocation>(CurrencyLocation.AFTER);
const { currencyLocation: location } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n();

function successMessage(currencyLocation: CurrencyLocation) {
  return t('general_settings.validation.currency_location.success', {
    currencyLocation,
  });
}

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
      data-cy="currency-location-input"
      class="flex flex-col"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    >
      <RuiRadio value="before">
        {{ t('general_settings.amount.label.location_before') }}
        <div class="text-sm text-rui-text-secondary mt-1">
          {{ t('general_settings.amount.example.before') }}
        </div>
      </RuiRadio>
      <RuiRadio value="after">
        {{ t('general_settings.amount.label.location_after') }}
        <div class="text-sm text-rui-text-secondary mt-1">
          {{ t('general_settings.amount.example.after') }}
        </div>
      </RuiRadio>
    </RuiRadioGroup>
  </SettingsOption>
</template>
