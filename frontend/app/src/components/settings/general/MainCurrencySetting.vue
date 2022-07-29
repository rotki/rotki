<template>
  <settings-option
    #default="{ error, success, update }"
    setting="mainCurrency"
    :error-message="$tc('general_settings.validation.currency.error')"
    :success-message="
      symbol =>
        $tc('general_settings.validation.currency.success', 0, {
          symbol
        })
    "
  >
    <v-select
      v-model="selectedCurrency"
      outlined
      class="general-settings__fields__currency-selector"
      :label="$t('general_settings.amount.labels.main_currency')"
      item-text="tickerSymbol"
      return-object
      :items="currencies"
      :success-messages="success"
      :error-messages="error"
      @change="update($event ? $event.tickerSymbol : $event)"
    >
      <template #item="{ item, attrs, on }">
        <v-list-item
          :id="`currency__${item.tickerSymbol.toLocaleLowerCase()}`"
          v-bind="attrs"
          v-on="on"
        >
          <v-list-item-avatar
            class="general-settings__currency-list primary--text"
          >
            {{ item.unicodeSymbol }}
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title>
              {{ item.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ $t('general_settings.amount.labels.main_currency_subtitle') }}
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </template>
    </v-select>
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { setupGeneralSettings } from '@/composables/session';
import { currencies } from '@/data/currencies';
import { Currency } from '@/types/currency';

const selectedCurrency = ref<Currency>(currencies[0]);
const { currency } = setupGeneralSettings();

onMounted(() => {
  set(selectedCurrency, get(currency));
});
</script>
