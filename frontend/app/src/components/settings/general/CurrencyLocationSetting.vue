<template>
  <settings-option
    #default="{ error, success, update }"
    setting="currencyLocation"
    frontend-setting
    :error-message="$tc('general_settings.validation.currency_location.error')"
    :success-message="
      currencyLocation =>
        $tc('general_settings.validation.currency_location.success', 0, {
          currencyLocation
        })
    "
  >
    <v-radio-group
      v-model="currencyLocation"
      class="general-settings__fields__currency-location"
      :label="$t('general_settings.amount.label.currency_location')"
      row
      :success-messages="success"
      :error-messages="error"
      @change="update"
    >
      <v-radio
        :label="$t('general_settings.amount.label.location_before')"
        value="before"
      />
      <v-radio
        :label="$t('general_settings.amount.label.location_after')"
        value="after"
      />
    </v-radio-group>
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { CurrencyLocation } from '@/types/currency-location';

const currencyLocation = ref<CurrencyLocation>(CurrencyLocation.AFTER);
const { currencyLocation: location } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(currencyLocation, get(location));
});
</script>
