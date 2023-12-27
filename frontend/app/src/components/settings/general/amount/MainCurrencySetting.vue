<script setup lang="ts">
import { type Currency, useCurrencies } from '@/types/currencies';

const { currencies } = useCurrencies();
const selectedCurrency = ref<Currency>(get(currencies)[0]);
const { currency } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const successMessage = (symbol: string) =>
  t('general_settings.validation.currency.success', {
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

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="mainCurrency"
    :error-message="t('general_settings.validation.currency.error')"
    :success-message="successMessage"
  >
    <VSelect
      v-model="selectedCurrency"
      outlined
      class="general-settings__fields__currency-selector"
      :label="t('general_settings.amount.labels.main_currency')"
      item-text="tickerSymbol"
      return-object
      :items="currencies"
      :success-messages="success"
      :error-messages="error"
      @change="update($event ? $event.tickerSymbol : $event)"
    >
      <template #item="{ item, attrs, on }">
        <ListItem
          :id="`currency__${item.tickerSymbol.toLocaleLowerCase()}`"
          no-hover
          no-padding
          size="lg"
          v-bind="attrs"
          :title="item.name"
          :subtitle="t('general_settings.amount.labels.main_currency_subtitle')"
          v-on="on"
        >
          <template #avatar>
            <div
              class="font-bold text-rui-primary"
              :style="{ fontSize: calculateFontSize(item.unicodeSymbol) }"
            >
              {{ item.unicodeSymbol }}
            </div>
          </template>
        </ListItem>
      </template>
    </VSelect>
  </SettingsOption>
</template>
