<script setup lang="ts">
import { type Currency, useCurrencies } from '@/types/currencies';

const { currencies } = useCurrencies();
const selectedCurrency = ref<Currency>(get(currencies)[0]);
const { currency } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

function successMessage(symbol: string) {
  return t('general_settings.validation.currency.success', {
    symbol,
  });
}

onMounted(() => {
  set(selectedCurrency, get(currency));
});

function calculateFontSize(symbol: string) {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
}
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
      variant="outlined"
      class="general-settings__fields__currency-selector"
      :label="t('general_settings.amount.labels.main_currency')"
      item-title="tickerSymbol"
      return-object
      :items="currencies"
      :messages="success"
      :error-messages="error"
      @update:model-value="update($event ? $event.tickerSymbol : $event)"
    >
      <template #item="{ item, props }">
        <ListItem
          :id="`currency__${item.raw.tickerSymbol.toLocaleLowerCase()}`"
          no-hover
          no-padding
          size="lg"
          v-bind="props"
          :title="item.raw.name"
          :subtitle="t('general_settings.amount.labels.main_currency_subtitle')"
        >
          <template #avatar>
            <div
              class="font-bold text-rui-primary"
              :style="{ fontSize: calculateFontSize(item.raw.unicodeSymbol) }"
            >
              {{ item.raw.unicodeSymbol }}
            </div>
          </template>
        </ListItem>
      </template>
    </VSelect>
  </SettingsOption>
</template>
