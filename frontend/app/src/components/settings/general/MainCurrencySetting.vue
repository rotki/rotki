<template>
  <settings-option
    #default="{ error, success, update }"
    setting="mainCurrency"
    :error-message="tc('general_settings.validation.currency.error')"
    :success-message="successMessage"
  >
    <v-select
      v-model="selectedCurrency"
      outlined
      class="general-settings__fields__currency-selector"
      :label="tc('general_settings.amount.labels.main_currency')"
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
            class="general-settings__currency-list primary--text font-weight-bold"
            :style="{ fontSize: calculateFontSize(item.unicodeSymbol) }"
          >
            {{ item.unicodeSymbol }}
          </v-list-item-avatar>
          <v-list-item-content>
            <v-list-item-title>
              {{ item.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ tc('general_settings.amount.labels.main_currency_subtitle') }}
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </template>
    </v-select>
  </settings-option>
</template>

<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';
import { currencies, Currency } from '@/types/currencies';

const selectedCurrency = ref<Currency>(currencies[0]);
const { currency } = storeToRefs(useGeneralSettingsStore());
const { tc } = useI18n();

const successMessage = (symbol: string) =>
  tc('general_settings.validation.currency.success', 0, {
    symbol
  });

onMounted(() => {
  set(selectedCurrency, get(currency));
});

const calculateFontSize = (symbol: string) => {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
};
</script>
